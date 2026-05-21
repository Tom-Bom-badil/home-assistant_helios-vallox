import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS, CONF_PORT
from .constants import DOMAIN, DEFAULT_IP, DEFAULT_PORT
from .constants import (
    DEVICE_PRESETS, CONF_DEVICE_MODEL, CONF_HOUSE_AREA, CONF_HOUSE_VOLUME,
    CONF_ISOLATION_FACTOR, CONF_AIRFLOW_PER_MODE, CONF_MAX_AIRFLOW,
    CONF_POWER_PER_MODE, CONF_MAX_POWER, CONF_HEATING_POWER, CUSTOM_MODEL,
)
from .vent_functions import HeliosBase

_LOGGER = logging.getLogger("helios_vallox.config_flow")


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
                await self.async_set_unique_id(f"{ip}:{port}")
                self._abort_if_unique_id_configured()
                self._data.update(user_input)
                return await self.async_step_model()
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_IP_ADDRESS, default=DEFAULT_IP): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )

    async def async_step_model(self, user_input=None):
        """Step 2: Select device model to pre-populate values."""
        if user_input is not None:
            model = user_input[CONF_DEVICE_MODEL]
            self._data[CONF_DEVICE_MODEL] = model
            return await self.async_step_details()

        model_options = list(DEVICE_PRESETS.keys()) + [CUSTOM_MODEL]
        return self.async_show_form(
            step_id="model",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_MODEL): vol.In(model_options),
                }
            ),
        )

    async def async_step_details(self, user_input=None):
        """Step 3: Device parameters (pre-populated from model selection)."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_house()

        # Pre-populate from selected model, or empty for custom
        model = self._data.get(CONF_DEVICE_MODEL, CUSTOM_MODEL)
        preset = DEVICE_PRESETS.get(model, {})

        return self.async_show_form(
            step_id="details",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_AIRFLOW_PER_MODE,
                        default=preset.get(CONF_AIRFLOW_PER_MODE, ""),
                    ): str,
                    vol.Required(
                        CONF_MAX_AIRFLOW,
                        default=preset.get(CONF_MAX_AIRFLOW),
                    ): vol.Coerce(int),
                    vol.Required(
                        CONF_POWER_PER_MODE,
                        default=preset.get(CONF_POWER_PER_MODE, ""),
                    ): str,
                    vol.Required(
                        CONF_MAX_POWER,
                        default=preset.get(CONF_MAX_POWER),
                    ): vol.Coerce(int),
                    vol.Required(
                        CONF_HEATING_POWER,
                        default=preset.get(CONF_HEATING_POWER),
                    ): vol.Coerce(int),
                }
            ),
        )

    async def async_step_house(self, user_input=None):
        """Step 4: House parameters."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title=f"Helios/Vallox ({self._data[CONF_IP_ADDRESS]})",
                data=self._data,
            )

        return self.async_show_form(
            step_id="house",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOUSE_AREA): vol.Coerce(float),
                    vol.Required(CONF_HOUSE_VOLUME): vol.Coerce(float),
                    vol.Required(CONF_ISOLATION_FACTOR, default=0.3): vol.Coerce(float),
                }
            ),
        )
