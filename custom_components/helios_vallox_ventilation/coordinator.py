import asyncio
import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .vent_functions import HeliosBase

_LOGGER = logging.getLogger(__name__)


class HeliosCoordinator:

    def __init__(self, hass: HomeAssistant, ip: str, port: int):
        self._hass = hass
        self._ip = ip
        self._port = port
        self._lock = asyncio.Lock()
        self.helios = HeliosBase(ip, port)
        self._coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="Helios_Vallox Data Coordinator",
            update_method=self._async_update_data,
            update_interval=timedelta(seconds=60),
        )
        _LOGGER.debug(f"DataUpdateCoordinator initialized: {self._coordinator}")


    @property
    def coordinator(self):
        return self._coordinator


    async def connect(self):
        try:
            _LOGGER.debug(f"Connecting to Helios system at {self._ip}:{self._port}...")
            connected = await self._hass.async_add_executor_job(self.helios._connect)
            return connected
        except Exception as e:
            _LOGGER.error(f"Failed to connect to Helios system: {e}", exc_info=True)
            return False


    def disconnect(self):
        self.helios._disconnect()


    async def _async_update_data(self):
        _LOGGER.debug("DataUpdateCoordinator: Fetching data...")
        try:
            data = await self._hass.async_add_executor_job(self.fetch_data_from_device)
            return data
        except Exception as e:
            _LOGGER.error(f"Error fetching data: {e}", exc_info=True)
            return {}


    def fetch_data_from_device(self):
        data = self.helios.readAllValues()
        return data


    async def setup_coordinator(self):
        if await self.connect():
            await self._coordinator.async_refresh()
        else:
            _LOGGER.error("Failed to connect to ventilation during setup.")


    async def trigger_manual_update(self):
        await self._coordinator.async_request_refresh()


    def write_value(self, variable, value):
        try:
            future = asyncio.run_coroutine_threadsafe(self.connect(), self._hass.loop)
            connected = future.result()
            if not connected:
                _LOGGER.error(f"Helios: Could not connect to the device.")
                return False
            result = self.helios.writeValue(variable, value)
            new_data = self._coordinator.data.copy() if self._coordinator.data else {}
            new_data[variable] = value
            self._hass.loop.call_soon_threadsafe(self._coordinator.async_set_updated_data, new_data)
            return result
        except Exception as e:
            _LOGGER.error(f"Error writing {value} to {variable}: {e}", exc_info=True)
            return False
        finally:
            self.disconnect()


    async def turn_on(self, variable):
        self._hass.async_add_executor_job(self.write_value, variable, 1)


    async def turn_off(self, variable):
        self._hass.async_add_executor_job(self.write_value, variable, 0)
