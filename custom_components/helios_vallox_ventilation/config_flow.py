import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import slugify
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)


from .api import HeliosBase
from .constants import (
    CUSTOM_MODEL,
    DEFAULT_ENTITY_PREFIX,
    DEVICE_PRESETS,
    DOMAIN,
    CONF_AIRFLOW_PER_MODE,
    CONF_DEVICE_MODEL,
    CONF_ENTITY_PREFIX,
    CONF_HEATING_POWER,
    CONF_HOUSE_AREA,
    CONF_HOUSE_VOLUME,
    CONF_ISOLATION_FACTOR,
    CONF_MAX_AIRFLOW,
    CONF_MAX_POWER,
    CONF_POWER_PER_MODE,
)


_LOGGER = logging.getLogger("helios_vallox.config_flow")


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


async def _async_can_connect(hass: HomeAssistant, ip: str, port: int) -> bool:
    """Check if the ventilation unit can be reached."""
    helios = HeliosBase(ip=ip, port=port)

    try:
        can_connect = await hass.async_add_executor_job(helios._connect)

        if can_connect:
            await hass.async_add_executor_job(helios._disconnect)
            return True

    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Connection test failed: %s", err)

    return False


def _parse_csv_values(value: str) -> list[int]:
    """Parse comma-separated integer values."""
    parts = [v.strip() for v in str(value or "").split(",") if v.strip()]
    return [int(v) for v in parts]


def _normalize_csv_without_off(value: str) -> str:
    """Normalize user input for fan speeds 1-8."""
    return ",".join(v.strip() for v in str(value or "").split(",") if v.strip())


def _csv_without_off(value: str | None) -> str:
    """Show fan speeds 1-8 in the UI, without internal speed 0."""
    parts = [v.strip() for v in str(value or "").split(",") if v.strip()]

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

    parts = [v.strip() for v in str(value or "").split(",") if v.strip()]

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


class HeliosValloxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Helios/Vallox ventilation."""

    VERSION = 1

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
        """Step 1: Connection settings (IP / port)."""
        errors = {}

        if user_input is not None:
            ip = user_input[CONF_IP_ADDRESS]
            port = user_input[CONF_PORT]

            if await _async_can_connect(self.hass, ip, port):
                await self.async_set_unique_id(
                    f"{ip}:{port}",
                    raise_on_progress=False,
                )
                self._abort_if_unique_id_configured()

                self._data.update(user_input)
                return await self.async_step_model()

            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_IP_ADDRESS): str,
                    vol.Required(CONF_PORT): int,
                }
            ),
            errors=errors,
        )

    async def async_step_model(self, user_input=None):
        """Step 2: Select a unique device name (=entity ID prefix) and the device model."""
        errors = {}

        if user_input is not None:
            entity_prefix = _normalize_entity_prefix(
                user_input.get(CONF_ENTITY_PREFIX, DEFAULT_ENTITY_PREFIX)
            )
            entity_prefix_slug = _build_entity_prefix_slug(entity_prefix)

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
        model = self._data.get(CONF_DEVICE_MODEL, CUSTOM_MODEL)
        preset = DEVICE_PRESETS.get(model, DEVICE_PRESETS[CUSTOM_MODEL])

        if user_input is not None:
            airflow_str = user_input.get(CONF_AIRFLOW_PER_MODE, "")
            power_str = user_input.get(CONF_POWER_PER_MODE, "")

            _validate_mode_csv(errors, CONF_AIRFLOW_PER_MODE, airflow_str)
            _validate_mode_csv(errors, CONF_POWER_PER_MODE, power_str)

            if not errors:
                user_input[CONF_AIRFLOW_PER_MODE] = _normalize_mode_csv_with_off(
                    airflow_str
                )
                user_input[CONF_POWER_PER_MODE] = _normalize_mode_csv_with_off(
                    power_str
                )

                user_input[CONF_MAX_AIRFLOW] = max(
                    _parse_csv_values(user_input[CONF_AIRFLOW_PER_MODE])
                )
                user_input[CONF_MAX_POWER] = max(
                    _parse_csv_values(user_input[CONF_POWER_PER_MODE])
                )

                self._data.update(user_input)
                return await self.async_step_house()

        return self.async_show_form(
            step_id="details",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_AIRFLOW_PER_MODE,
                        default=preset.get(CONF_AIRFLOW_PER_MODE, "0,0,0,0,0,0,0,0"),
                    ): str,
                    vol.Required(
                        CONF_POWER_PER_MODE,
                        default=preset.get(CONF_POWER_PER_MODE, "0,0,0,0,0,0,0,0"),
                    ): str,
                    vol.Required(
                        CONF_HEATING_POWER,
                        default=preset.get(CONF_HEATING_POWER, 0),
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
                title=self._data.get(CONF_ENTITY_PREFIX, DEFAULT_ENTITY_PREFIX),
                data=self._data,
            )

        model = self._data.get(CONF_DEVICE_MODEL, CUSTOM_MODEL)
        preset = DEVICE_PRESETS.get(model, DEVICE_PRESETS[CUSTOM_MODEL])

        return self.async_show_form(
            step_id="house",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOUSE_AREA,
                        default=preset.get(CONF_HOUSE_AREA, 0),
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_HOUSE_VOLUME,
                        default=preset.get(CONF_HOUSE_VOLUME, 0),
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_ISOLATION_FACTOR,
                        default=preset.get(CONF_ISOLATION_FACTOR, 0.3),
                    ): vol.Coerce(float),
                }
            ),
        )


class HeliosValloxOptionsFlowHandler(config_entries.OptionsFlowWithReload):
    """Options flow for editable Helios/Vallox configuration values."""

    async def async_step_init(self, user_input=None):
        """Edit connection, ventilation and house parameters."""
        errors = {}

        if user_input is not None:
            ip = user_input[CONF_IP_ADDRESS]
            port = user_input[CONF_PORT]

            if not await _async_can_connect(self.hass, ip, port):
                errors["base"] = "cannot_connect"

            airflow_str = user_input.get(CONF_AIRFLOW_PER_MODE, "")
            power_str = user_input.get(CONF_POWER_PER_MODE, "")

            _validate_mode_csv(errors, CONF_AIRFLOW_PER_MODE, airflow_str)
            _validate_mode_csv(errors, CONF_POWER_PER_MODE, power_str)

            if not errors:
                options = dict(self.config_entry.options)

                options.update(user_input)
                options[CONF_AIRFLOW_PER_MODE] = _normalize_mode_csv_with_off(
                    airflow_str
                )
                options[CONF_POWER_PER_MODE] = _normalize_mode_csv_with_off(
                    power_str
                )
                options[CONF_MAX_AIRFLOW] = max(
                    _parse_csv_values(options[CONF_AIRFLOW_PER_MODE])
                )
                options[CONF_MAX_POWER] = max(
                    _parse_csv_values(options[CONF_POWER_PER_MODE])
                )

                return self.async_create_entry(title="", data=options)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_IP_ADDRESS,
                        default=self._get_entry_value(CONF_IP_ADDRESS, ""),
                    ): str,
                    vol.Required(
                        CONF_PORT,
                        default=self._get_entry_value(CONF_PORT, 26),
                    ): vol.Coerce(int),
                    vol.Required(
                        CONF_AIRFLOW_PER_MODE,
                        default=_csv_without_off(
                            self._get_entry_value(CONF_AIRFLOW_PER_MODE, "")
                        ),
                    ): str,
                    vol.Required(
                        CONF_POWER_PER_MODE,
                        default=_csv_without_off(
                            self._get_entry_value(CONF_POWER_PER_MODE, "")
                        ),
                    ): str,
                    vol.Required(
                        CONF_HEATING_POWER,
                        default=self._get_entry_value(CONF_HEATING_POWER, 0),
                    ): vol.Coerce(int),
                    vol.Required(
                        CONF_HOUSE_AREA,
                        default=self._get_entry_value(CONF_HOUSE_AREA, 0),
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_HOUSE_VOLUME,
                        default=self._get_entry_value(CONF_HOUSE_VOLUME, 0),
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_ISOLATION_FACTOR,
                        default=self._get_entry_value(CONF_ISOLATION_FACTOR, 0.3),
                    ): vol.Coerce(float),
                }
            ),
            errors=errors,
        )

    def _get_entry_value(self, key: str, default=None):
        """Return option value first, then config data value."""
        return self.config_entry.options.get(
            key,
            self.config_entry.data.get(key, default),
        )