import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from .constants import DOMAIN
from .coordinator import HeliosCoordinator
from .schema import SERVICE_WRITE_VALUE_SCHEMA

_LOGGER = logging.getLogger("helios_vallox.__init__")

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH, Platform.NUMBER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ip_address = entry.data[CONF_IP_ADDRESS]
    port = entry.data[CONF_PORT]

    coordinator = HeliosCoordinator(hass, ip_address, port)
    await coordinator.setup_coordinator()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register write service (once per domain)
    if not hass.services.has_service(DOMAIN, "write_value"):
        async def handle_write_service(call):
            target_entry_id = call.data["entry_id"]
            coord = hass.data[DOMAIN].get(target_entry_id)
            if coord is None:
                _LOGGER.error(f"No device found for entry_id: {target_entry_id}")
                return
            try:
                await hass.async_add_executor_job(
                    coord.write_value, call.data["variable"], call.data["value"]
                )
            except Exception as e:
                _LOGGER.error(f"Error handling write service: {e}", exc_info=True)

        hass.services.async_register(
            DOMAIN, "write_value", handle_write_service, schema=SERVICE_WRITE_VALUE_SCHEMA
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "write_value")
    return unload_ok
