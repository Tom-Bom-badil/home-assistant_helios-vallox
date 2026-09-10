import logging
from urllib.parse import parse_qs, urlsplit

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SerialPortSelector,
    TextSelector,
)
from homeassistant.util import slugify

from .api import HeliosBase
from .constants import (
    CONF_AIRFLOW_PER_MODE,
    CONF_CONNECTION,
    CONF_DEVICE_MODEL,
    CONF_ENTITY_PREFIX,
    CONF_HEATING_POWER,
    CONF_HOUSE_AREA,
    CONF_HOUSE_VOLUME,
    CONF_ISOLATION_FACTOR,
    CONF_KNOWN_CONNECTION,
    CONF_MAX_AIRFLOW,
    CONF_MAX_POWER,
    CONF_POWER_PER_MODE,
    CUSTOM_MODEL,
    DEFAULT_ENTITY_PREFIX,
    DEVICE_PRESETS,
    DOMAIN,
)


_LOGGER = logging.getLogger("helios_vallox.config_flow")


def _connection_schema() -> vol.Schema:
    """Return the unified connection schema."""
    return vol.Schema(
        {
            vol.Optional(CONF_KNOWN_CONNECTION): SerialPortSelector(),
            vol.Optional(CONF_CONNECTION): TextSelector(),
        }
    )


def _selected_connection(user_input: dict) -> str | None:
    """Return the selected connection target.

    A known Home Assistant serial interface takes precedence over the manual
    field. This makes it possible to switch an existing socket connection to
    a detected local or ESPHome serial interface without clearing the manual
    field first.
    """
    known = str(user_input.get(CONF_KNOWN_CONNECTION) or "").strip()
    if known:
        return known

    manual = str(user_input.get(CONF_CONNECTION) or "").strip()
    return manual or None


def _normalize_connection(value: str) -> str:
    """Validate and normalize a user-facing connection target."""
    connection = value.strip()
    lowered = connection.lower()

    if lowered.startswith("/dev/"):
        return connection

    if lowered.startswith("socket://"):
        parsed = urlsplit(connection)

        if (
            parsed.scheme.lower() != "socket"
            or parsed.hostname is None
            or parsed.port is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Invalid socket connection")

        return connection

    if lowered.startswith("esphome-hass://"):
        parsed = urlsplit(connection)
        query = parse_qs(parsed.query)

        if (
            parsed.scheme.lower() != "esphome-hass"
            or parsed.hostname != "esphome"
            or not parsed.path.strip("/")
            or not query.get("port_name")
        ):
            raise ValueError("Invalid Home Assistant ESPHome serial proxy")

        return connection

    raise ValueError("Unsupported connection")


def _format_host_port(host: str, port: int) -> str:
    """Return host:port with brackets around an IPv6 literal."""
    formatted_host = (
        f"[{host}]"
        if ":" in host and not host.startswith("[")
        else host
    )
    return f"{formatted_host}:{port}"


def _connection_unique_id(connection: str) -> str:
    """Return a stable unique ID for a connection target.

    Legacy network config entries used host:port as their unique ID. Keep the
    same representation for socket connections so an existing adapter cannot
    accidentally be configured a second time after migration.
    """
    if connection.lower().startswith("socket://"):
        parsed = urlsplit(connection)

        if parsed.hostname is not None and parsed.port is not None:
            return _format_host_port(parsed.hostname, parsed.port)

    return connection


async def _async_can_connect(
    hass: HomeAssistant,
    connection: str,
) -> bool:
    """Check whether the configured transport can be opened."""
    helios = HeliosBase(connection=connection)

    try:
        return await hass.async_add_executor_job(helios._connect)

    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Connection test failed: %s", err)
        return False

    finally:
        try:
            await hass.async_add_executor_job(helios._disconnect)
        except Exception:  # noqa: BLE001
            pass


def _normalize_entity_prefix(value: str | None) -> str:
    """Normalize the user-visible entity prefix."""
    return str(value or "").strip()


def _build_entity_prefix_slug(value: str | None) -> str:
    """Build a slug from the user-visible entity prefix."""
    return slugify(_normalize_entity_prefix(value))


def _get_saved_entity_prefix(entry: config_entries.ConfigEntry) -> str:
    """Return the saved entity prefix from options or data."""
    return _normalize_entity_prefix(
        entry.options.get(
            CONF_ENTITY_PREFIX,
            entry.data.get(CONF_ENTITY_PREFIX, DEFAULT_ENTITY_PREFIX),
        )
    )


def _is_entity_prefix_in_use(
    entries: list[config_entries.ConfigEntry],
    prefix: str,
) -> bool:
    """Check if the entity prefix is already used by another config entry."""
    candidate_slug = _build_entity_prefix_slug(prefix)

    if not candidate_slug:
        return False

    for entry in entries:
        existing_prefix = _get_saved_entity_prefix(entry)
        if _build_entity_prefix_slug(existing_prefix) == candidate_slug:
            return True

    return False


def _parse_csv_values(value: str) -> list[int]:
    """Parse comma-separated integer values."""
    parts = [
        v.strip()
        for v in str(value or "").split(",")
        if v.strip()
    ]
    return [int(v) for v in parts]


def _normalize_csv_without_off(value: str) -> str:
    """Normalize user input for fan speeds 1-8."""
    return ",".join(
        v.strip()
        for v in str(value or "").split(",")
        if v.strip()
    )


def _csv_without_off(value: str | None) -> str:
    """Show fan speeds 1-8 in the UI, without internal speed 0."""
    parts = [
        v.strip()
        for v in str(value or "").split(",")
        if v.strip()
    ]

    if len(parts) == 9 and parts[0] == "0":
        parts = parts[1:]

    return ",".join(parts)


def _validate_mode_csv(
    errors: dict[str, str],
    field: str,
    value: str,
) -> None:
    """Validate a comma-separated list of exactly 8 integer values."""
    if not str(value or "").strip():
        errors[field] = "invalid_csv_count"
        return

    parts = [
        v.strip()
        for v in str(value or "").split(",")
        if v.strip()
    ]

    if len(parts) != 8:
        errors[field] = "invalid_csv_count"
        return

    try:
        [int(v) for v in parts]
    except ValueError:
        errors[field] = "invalid_csv_values"


def _normalize_mode_csv_with_off(value: str) -> str:
    """Normalize user input and prepend internal fan speed 0."""
    return "0," + _normalize_csv_without_off(value)


class HeliosValloxConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Config flow for Helios/Vallox ventilation."""

    VERSION = 2

    def __init__(self):
        self._data = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        _config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return HeliosValloxOptionsFlowHandler()

    async def async_step_user(self, user_input=None):
        """Step 1: Select or enter the connection."""
        errors = {}

        if user_input is not None:
            connection = _selected_connection(user_input)

            if connection is None:
                errors[CONF_CONNECTION] = "connection_required"

            else:
                try:
                    connection = _normalize_connection(connection)
                except ValueError:
                    errors[CONF_CONNECTION] = "invalid_connection"

                else:
                    if await _async_can_connect(
                        self.hass,
                        connection,
                    ):
                        await self.async_set_unique_id(
                            _connection_unique_id(connection),
                            raise_on_progress=False,
                        )
                        self._abort_if_unique_id_configured()

                        self._data[CONF_CONNECTION] = connection
                        return await self.async_step_model()

                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=_connection_schema(),
            errors=errors,
        )

    async def async_step_model(self, user_input=None):
        """Step 2: Select a unique device name (=entity ID prefix) and the device model."""
        errors = {}

        if user_input is not None:
            entity_prefix = _normalize_entity_prefix(
                user_input.get(
                    CONF_ENTITY_PREFIX,
                    DEFAULT_ENTITY_PREFIX,
                )
            )
            entity_prefix_slug = _build_entity_prefix_slug(
                entity_prefix
            )

            if not entity_prefix or not entity_prefix_slug:
                errors["base"] = "invalid_entity_prefix"

            elif _is_entity_prefix_in_use(
                self.hass.config_entries.async_entries(DOMAIN),
                entity_prefix,
            ):
                errors["base"] = "entity_prefix_in_use"

            else:
                model = user_input[CONF_DEVICE_MODEL]
                self._data[CONF_DEVICE_MODEL] = model
                self._data[CONF_ENTITY_PREFIX] = entity_prefix
                return await self.async_step_details()

        model_options = list(DEVICE_PRESETS.keys())

        return self.async_show_form(
            step_id="model",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENTITY_PREFIX,
                        default=DEFAULT_ENTITY_PREFIX,
                    ): str,
                    vol.Required(
                        CONF_DEVICE_MODEL,
                        default=CUSTOM_MODEL,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=model_options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_details(self, user_input=None):
        """Step 3: Device parameters (pre-populated from model selection)."""
        errors = {}
        model = self._data.get(
            CONF_DEVICE_MODEL,
            CUSTOM_MODEL,
        )
        preset = DEVICE_PRESETS.get(
            model,
            DEVICE_PRESETS[CUSTOM_MODEL],
        )

        if user_input is not None:
            airflow_str = user_input.get(
                CONF_AIRFLOW_PER_MODE,
                "",
            )
            power_str = user_input.get(
                CONF_POWER_PER_MODE,
                "",
            )

            _validate_mode_csv(
                errors,
                CONF_AIRFLOW_PER_MODE,
                airflow_str,
            )
            _validate_mode_csv(
                errors,
                CONF_POWER_PER_MODE,
                power_str,
            )

            if not errors:
                user_input[
                    CONF_AIRFLOW_PER_MODE
                ] = _normalize_mode_csv_with_off(
                    airflow_str
                )
                user_input[
                    CONF_POWER_PER_MODE
                ] = _normalize_mode_csv_with_off(
                    power_str
                )
                user_input[CONF_MAX_AIRFLOW] = max(
                    _parse_csv_values(
                        user_input[CONF_AIRFLOW_PER_MODE]
                    )
                )
                user_input[CONF_MAX_POWER] = max(
                    _parse_csv_values(
                        user_input[CONF_POWER_PER_MODE]
                    )
                )

                self._data.update(user_input)
                return await self.async_step_house()

        return self.async_show_form(
            step_id="details",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_AIRFLOW_PER_MODE,
                        default=preset.get(
                            CONF_AIRFLOW_PER_MODE,
                            "0,0,0,0,0,0,0,0",
                        ),
                    ): str,
                    vol.Required(
                        CONF_POWER_PER_MODE,
                        default=preset.get(
                            CONF_POWER_PER_MODE,
                            "0,0,0,0,0,0,0,0",
                        ),
                    ): str,
                    vol.Required(
                        CONF_HEATING_POWER,
                        default=preset.get(
                            CONF_HEATING_POWER,
                            0,
                        ),
                    ): vol.Coerce(int),
                }
            ),
            errors=errors,
        )

    async def async_step_house(self, user_input=None):
        """Step 4: House parameters."""
        if user_input is not None:
            self._data.update(user_input)

            return self.async_create_entry(
                title=self._data.get(
                    CONF_ENTITY_PREFIX,
                    DEFAULT_ENTITY_PREFIX,
                ),
                data=self._data,
            )

        model = self._data.get(
            CONF_DEVICE_MODEL,
            CUSTOM_MODEL,
        )
        preset = DEVICE_PRESETS.get(
            model,
            DEVICE_PRESETS[CUSTOM_MODEL],
        )

        return self.async_show_form(
            step_id="house",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOUSE_AREA,
                        default=preset.get(
                            CONF_HOUSE_AREA,
                            0,
                        ),
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_HOUSE_VOLUME,
                        default=preset.get(
                            CONF_HOUSE_VOLUME,
                            0,
                        ),
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_ISOLATION_FACTOR,
                        default=preset.get(
                            CONF_ISOLATION_FACTOR,
                            0.3,
                        ),
                    ): vol.Coerce(float),
                }
            ),
        )


class HeliosValloxOptionsFlowHandler(
    config_entries.OptionsFlowWithReload
):
    """Options flow for editable Helios/Vallox configuration values."""

    def __init__(self) -> None:
        self._pending_connection: str | None = None

    async def async_step_init(self, user_input=None):
        """Step 1: Edit the connection."""
        errors = {}

        if user_input is not None:
            connection = _selected_connection(user_input)

            if connection is None:
                errors[CONF_CONNECTION] = "connection_required"

            else:
                try:
                    connection = _normalize_connection(connection)
                except ValueError:
                    errors[CONF_CONNECTION] = "invalid_connection"

                else:
                    if await _async_can_connect(
                        self.hass,
                        connection,
                    ):
                        self._pending_connection = connection
                        return await self.async_step_advanced()

                    errors["base"] = "cannot_connect"

        current_connection = self._get_entry_value(
            CONF_CONNECTION,
            "",
        )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _connection_schema(),
                {
                    CONF_CONNECTION: current_connection,
                },
            ),
            errors=errors,
        )

    async def async_step_advanced(self, user_input=None):
        """Step 2: Edit ventilation and house parameters."""
        if self._pending_connection is None:
            return await self.async_step_init()

        errors = {}

        if user_input is not None:
            airflow_str = user_input.get(
                CONF_AIRFLOW_PER_MODE,
                "",
            )
            power_str = user_input.get(
                CONF_POWER_PER_MODE,
                "",
            )

            _validate_mode_csv(
                errors,
                CONF_AIRFLOW_PER_MODE,
                airflow_str,
            )
            _validate_mode_csv(
                errors,
                CONF_POWER_PER_MODE,
                power_str,
            )

            if not errors:
                options = dict(self.config_entry.options)
                options.update(user_input)

                options[
                    CONF_CONNECTION
                ] = self._pending_connection

                options[
                    CONF_AIRFLOW_PER_MODE
                ] = _normalize_mode_csv_with_off(
                    airflow_str
                )
                options[
                    CONF_POWER_PER_MODE
                ] = _normalize_mode_csv_with_off(
                    power_str
                )

                options[CONF_MAX_AIRFLOW] = max(
                    _parse_csv_values(
                        options[CONF_AIRFLOW_PER_MODE]
                    )
                )
                options[CONF_MAX_POWER] = max(
                    _parse_csv_values(
                        options[CONF_POWER_PER_MODE]
                    )
                )

                return self.async_create_entry(
                    title="",
                    data=options,
                )

        return self.async_show_form(
            step_id="advanced",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_AIRFLOW_PER_MODE,
                        default=_csv_without_off(
                            self._get_entry_value(
                                CONF_AIRFLOW_PER_MODE,
                                "",
                            )
                        ),
                    ): str,
                    vol.Required(
                        CONF_POWER_PER_MODE,
                        default=_csv_without_off(
                            self._get_entry_value(
                                CONF_POWER_PER_MODE,
                                "",
                            )
                        ),
                    ): str,
                    vol.Required(
                        CONF_HEATING_POWER,
                        default=self._get_entry_value(
                            CONF_HEATING_POWER,
                            0,
                        ),
                    ): vol.Coerce(int),
                    vol.Required(
                        CONF_HOUSE_AREA,
                        default=self._get_entry_value(
                            CONF_HOUSE_AREA,
                            0,
                        ),
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_HOUSE_VOLUME,
                        default=self._get_entry_value(
                            CONF_HOUSE_VOLUME,
                            0,
                        ),
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_ISOLATION_FACTOR,
                        default=self._get_entry_value(
                            CONF_ISOLATION_FACTOR,
                            0.3,
                        ),
                    ): vol.Coerce(float),
                }
            ),
            errors=errors,
        )

    def _get_entry_value(self, key: str, default=None):
        """Return option value first, then config data value."""
        return self.config_entry.options.get(
            key,
            self.config_entry.data.get(
                key,
                default,
            ),
        )
