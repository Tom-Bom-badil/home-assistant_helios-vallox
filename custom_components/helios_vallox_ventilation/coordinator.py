import asyncio
import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .vent_functions import HeliosBase
from .constants import DEVELOPER_MODE

# _LOGGER = logging.getLogger(__name__)
_LOGGER = logging.getLogger("helios_vallox.coordinator")

class HeliosCoordinator:

    # Initialize data update coordinator
    def __init__(self, hass: HomeAssistant, ip: str, port: int, config_data: dict = None):
        self._hass = hass
        self._ip = ip
        self._port = port
        self._lock = asyncio.Lock()
        self._capabilities = {"co2": False, "rh": False}
        self._helios = HeliosBase(hass, ip, port, config_data=config_data)
        self._coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="Helios Vallox Data Coordinator",
            update_method=self._async_update_data,
            update_interval=timedelta(seconds=59), # see also __init__.py
        )

    # Declare coordinator property
    @property
    def coordinator(self):
        return self._coordinator

    # Setup the coordinator
    async def setup_coordinator(self):
        if await self._hass.async_add_executor_job(self._helios._connect):
            await self._coordinator.async_refresh()
        else:
            _LOGGER.error("Failed to connect to ventilation during setup.")

    # Read all known registers (see vent_conf.yaml and const.py)
    async def _async_update_data(self):
        try:
            data = await self._hass.async_add_executor_job(self._helios.readAllValues)
            self._capabilities = (
                {"co2": True, "rh": True}
                if DEVELOPER_MODE
                else self._detect_capabilities(data)
            )
            return data
        except Exception as e:
            _LOGGER.error(f"Error fetching data: {e}", exc_info=True)
            return {}

    def has_capability(self, capability: str) -> bool:
        """Return True if the ventilation unit supports the given capability."""
        return self._capabilities.get(capability, False)

    @staticmethod
    def _detect_capabilities(data: dict | None) -> dict[str, bool]:
        """Detect optional hardware features from the latest read data."""
        data = data or {}
        return {
            "co2": any(data.get(f"co2_sensor{i}_present") for i in range(1, 6)),
            "rh": any(
                HeliosCoordinator._is_valid_rh_raw(data.get(key))
                for key in ("rh_sensor1_raw", "rh_sensor2_raw")
            ),
        }

    @staticmethod
    def _is_valid_rh_raw(value) -> bool:
        """Return True if a raw humidity value looks like a real sensor value."""
        try:
            return 0x33 <= int(value) <= 0xFF
        except (TypeError, ValueError):
            return False

    # Write a single register
    def write_value(self, variable, value, min_value=None, max_value=None):
        try:
            result = self._helios.writeValue(variable, value, min_value, max_value)
            if result:
                new_data = self._coordinator.data.copy() if self._coordinator.data else {}
                new_data[variable] = value
                self._hass.loop.call_soon_threadsafe(self._coordinator.async_set_updated_data, new_data)
            return result
        except Exception as e:
            _LOGGER.error(f"Error writing {value} to {variable}: {e}", exc_info=True)
            return False

    # Special treatment for two combined 16-bit registers (here: CO2 setpoint)
    def write_co2_setting_value(self, value, min_value=None, max_value=None):
        try:
            value = int(round(float(value) / 50) * 50)
            if min_value is not None:
                value = max(int(min_value), value)
            if max_value is not None:
                value = min(int(max_value), value)
            lower = value % 256
            upper = value // 256
            # Always write the lower byte first. The mainboard appears to latch / apply
            # the 16-bit CO2 setpoint when the upper byte is written.
            lower_ok = self._helios.writeValue("co2_setting_lower_byte", lower, 0, 255)
            upper_ok = self._helios.writeValue("co2_setting_upper_byte", upper, 0, 255)
            if upper_ok and lower_ok:
                new_data = self._coordinator.data.copy() if self._coordinator.data else {}
                new_data["co2_setting_upper_byte"] = upper
                new_data["co2_setting_lower_byte"] = lower
                new_data["co2_setting_value"] = value
                self._hass.loop.call_soon_threadsafe(
                    self._coordinator.async_set_updated_data,
                    new_data,
                )
                return True
        except Exception as e:
            _LOGGER.error("Error writing CO2 setting value %s: %s", value, e, exc_info=True)
        return False

    # Switch: Turn on
    async def turn_on(self, variable):
        self._hass.async_add_executor_job(self.write_value, variable, 1)

    # Switch: Turn off
    async def turn_off(self, variable):
        self._hass.async_add_executor_job(self.write_value, variable, 0)
