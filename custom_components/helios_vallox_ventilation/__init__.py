import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta
from .const import DOMAIN
from .coordinator import HeliosCoordinator
from .schema import CONFIG_SCHEMA
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):

    # Validate and load configuration
    config = CONFIG_SCHEMA(config)
    ip_address = config[DOMAIN].get("ip_address", "192.168.178.36")
    port = config[DOMAIN].get("port", 502)
    _LOGGER.debug(f"Initializing HeliosCoordinator with IP: {ip_address}, Port: {port}")

    # Initialize coordinator
    coordinator = HeliosCoordinator(hass, ip_address, port)
    hass.data[DOMAIN] = {
        "coordinator": coordinator,
        "entities": []
    }

    # Set up the update coordinator
    await coordinator.setup_coordinator()

    # Load platforms for entities
    hass.async_create_task(
        async_load_platform(hass, "sensor", DOMAIN, {"sensors": config[DOMAIN].get("sensors", [])}, config)
    )
    hass.async_create_task(
        async_load_platform(hass, "binary_sensor", DOMAIN, {"binary_sensors": config[DOMAIN].get("binary_sensors", [])}, config)
    )
    hass.async_create_task(
        async_load_platform(hass, "switch", DOMAIN, {"switches": config[DOMAIN].get("switches", [])}, config)
    )

    # Set up periodic data refresh
    async def update_data(_):
        try:
            await coordinator._coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Error during data refresh: {e}", exc_info=True)
    async_track_time_interval(hass, update_data, timedelta(seconds=23))

    # Register the write service
    async def handle_write_service(call):
        variable = call.data.get("variable")
        value = call.data.get("value")
        if not variable or value is None:
            _LOGGER.error("Service call missing 'variable' or 'value'.")
            return
        try:
            success = await hass.async_add_executor_job(coordinator.write_value, variable, value)
            if success:
                _LOGGER.debug(f"Successfully wrote {value} to {variable}.")
            else:
                _LOGGER.error(f"Failed to write {value} to {variable}.")
        except Exception as e:
            _LOGGER.error(f"Error handling write service: {e}", exc_info=True)
    hass.services.async_register(
        DOMAIN, "write_value", handle_write_service, schema=CONFIG_SCHEMA
    )

    # Initialization done
    return True


# Set up the integration from a config entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    return await async_setup(hass, entry.data)


# Unload the integration
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.pop(DOMAIN, None)
    return True
