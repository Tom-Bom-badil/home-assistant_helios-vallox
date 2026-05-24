import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS, CONF_PORT
from homeassistant.util import slugify
from .constants import (
    DOMAIN,
    DEVICE_PRESETS,
    CONF_DEVICE_MODEL,
    CONF_HOUSE_AREA,
    CONF_HOUSE_VOLUME,
    CONF_ISOLATION_FACTOR,
    CONF_AIRFLOW_PER_MODE,
    CONF_MAX_AIRFLOW,
    CONF_POWER_PER_MODE,
    CONF_MAX_POWER,
    CONF_HEATING_POWER,
    CUSTOM_MODEL,
    CONF_ENTITY_PREFIX,
    DEFAULT_ENTITY_PREFIX,
)
from .vent_functions import HeliosBase

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


class HeliosValloxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Helios/Vallox ventilation."""

    VERSION = 1

    def __init__(self):
        self._data = {}

    async def async_step_user(self, user_input=None):
        """Step 1: Connection settings (IP / port)."""
        errors = {}
        if user_input is not None:
            ip = user_input[CONF_IP_ADDRESS]
            port = user_input[CONF_PORT]

            helios = HeliosBase(ip=ip, port=port)
            can_connect = await self.hass.async_add_executor_job(helios._connect)
            if can_connect:
                await self.hass.async_add_executor_job(helios._disconnect)
                await self.async_set_unique_id(
                    f"{ip}:{port}", raise_on_progress=False
                )
                self._abort_if_unique_id_configured()
                self._data.update(user_input)
                return await self.async_step_model()
            else:
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
        """Step 2: Select device model and unique device name."""
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

        model_options = list(DEVICE_PRESETS.keys()) + [CUSTOM_MODEL]

        return self.async_show_form(
            step_id="model",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENTITY_PREFIX,
                        default=DEFAULT_ENTITY_PREFIX,
                    ): str,
                    vol.Required(CONF_DEVICE_MODEL): vol.In(model_options),
                }
            ),
            errors=errors,
        )


    async def async_step_details(self, user_input=None):
        """Step 3: Device parameters (pre-populated from model selection)."""
        errors = {}
        if user_input is not None:
            # Validate comma-separated fields: must be exactly 8 integers
            airflow_str = user_input.get(CONF_AIRFLOW_PER_MODE, "")
            power_str = user_input.get(CONF_POWER_PER_MODE, "")

            for field, value in [
                (CONF_AIRFLOW_PER_MODE, airflow_str),
                (CONF_POWER_PER_MODE, power_str),
            ]:
                if value:
                    parts = [v.strip() for v in value.split(",") if v.strip()]
                    if len(parts) != 8:
                        errors[field] = "invalid_csv_count"
                        continue
                    try:
                        [int(v) for v in parts]
                    except ValueError:
                        errors[field] = "invalid_csv_values"

            if not errors:
                # Normalize: trim spaces and prepend 0 for fan speed 0 (off)
                if airflow_str:
                    trimmed = ",".join(v.strip() for v in airflow_str.split(",") if v.strip())
                    user_input[CONF_AIRFLOW_PER_MODE] = "0," + trimmed
                if power_str:
                    trimmed = ",".join(v.strip() for v in power_str.split(",") if v.strip())
                    user_input[CONF_POWER_PER_MODE] = "0," + trimmed
                # Compute max airflow/power from the normalized per-mode values
                if user_input.get(CONF_AIRFLOW_PER_MODE):
                    user_input[CONF_MAX_AIRFLOW] = max(
                        int(v) for v in user_input[CONF_AIRFLOW_PER_MODE].split(",")
                    )
                if user_input.get(CONF_POWER_PER_MODE):
                    user_input[CONF_MAX_POWER] = max(
                        int(v) for v in user_input[CONF_POWER_PER_MODE].split(",")
                    )
                self._data.update(user_input)
                return await self.async_step_house()

        # Pre-populate from selected model, or empty for custom
        model = self._data.get(CONF_DEVICE_MODEL, CUSTOM_MODEL)
        preset = DEVICE_PRESETS.get(model, {})

        return self.async_show_form(
            step_id="details",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_AIRFLOW_PER_MODE,
                        default=preset.get(CONF_AIRFLOW_PER_MODE, ""),
                    ): str,
                    vol.Optional(
                        CONF_POWER_PER_MODE,
                        default=preset.get(CONF_POWER_PER_MODE, ""),
                    ): str,
                    vol.Optional(
                        CONF_HEATING_POWER,
                        default=preset.get(CONF_HEATING_POWER),
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

        return self.async_show_form(
            step_id="house",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_HOUSE_AREA): vol.Coerce(float),
                    vol.Optional(CONF_HOUSE_VOLUME): vol.Coerce(float),
                    vol.Optional(CONF_ISOLATION_FACTOR, default=0.3): vol.Coerce(float),
                }
            ),
        )
