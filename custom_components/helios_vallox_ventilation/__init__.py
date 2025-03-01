import logging
from .const import DOMAIN
from .schema import CONFIG_SCHEMA
from .coordinator import HeliosCoordinator
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.event import async_track_time_interval

# _LOGGER = logging.getLogger(__name__)   # too long, shortening
_LOGGER = logging.getLogger("helios_vallox.__init__")

async def async_setup(hass: HomeAssistant, config: dict):

    # Validate and load configuration
    config = CONFIG_SCHEMA(config)
    ip_address = config[DOMAIN].get("ip_address", "192.168.178.36")
    port = config[DOMAIN].get("port", 502)

    # Initialize and setup coordinator
    coordinator = HeliosCoordinator(hass, ip_address, port)
    hass.data[DOMAIN] = {"coordinator": coordinator, "entities": []}
    await coordinator.setup_coordinator()

    # Load entity platforms
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

    # Register and manage the write service
    async def handle_write_service(call):
        try:
            await hass.async_add_executor_job(coordinator.write_value, call.data["variable"], call.data["value"])
        except Exception as e:
            _LOGGER.error(f"Error handling write service: {e}", exc_info=True)
    hass.services.async_register(DOMAIN, "write_value", handle_write_service, schema=CONFIG_SCHEMA)

    # Initialization done
    return True

# Setup from config
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    return await async_setup(hass, entry.data)

# Unload integration
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.pop(DOMAIN, None)
    return True
