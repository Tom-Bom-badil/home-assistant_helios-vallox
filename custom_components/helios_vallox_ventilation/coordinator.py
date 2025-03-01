import asyncio
import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .vent_functions import HeliosBase

# _LOGGER = logging.getLogger(__name__)
_LOGGER = logging.getLogger("helios_vallox.coordinator")

class HeliosCoordinator:

    # Initialize data update coordinator
    def __init__(self, hass: HomeAssistant, ip: str, port: int):
        self._hass = hass
        self._ip = ip
        self._port = port
        self._lock = asyncio.Lock()
        self._helios = HeliosBase(hass, ip, port)
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
            return data
        except Exception as e:
            _LOGGER.error(f"Error fetching data: {e}", exc_info=True)
            return {}

    # Write a single register
    def write_value(self, variable, value):
        try:
            result = self._helios.writeValue(variable, value)
            if result:
                new_data = self._coordinator.data.copy() if self._coordinator.data else {}
                new_data[variable] = value
                self._hass.loop.call_soon_threadsafe(self._coordinator.async_set_updated_data, new_data)
            return result
        except Exception as e:
            _LOGGER.error(f"Error writing {value} to {variable}: {e}", exc_info=True)
            return False

    # Switch: Turn on
    async def turn_on(self, variable):
        self._hass.async_add_executor_job(self.write_value, variable, 1)

    # Switch: Turn off
    async def turn_off(self, variable):
        self._hass.async_add_executor_job(self.write_value, variable, 0)
