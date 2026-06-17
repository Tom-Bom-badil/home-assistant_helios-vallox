import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .constants import DOMAIN
from .device_info import build_device_info, build_entity_id

_LOGGER = logging.getLogger("helios_vallox.button")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        HeliosResetServiceReminderButton(coordinator, entry),
    ])


class HeliosResetServiceReminderButton(CoordinatorEntity, ButtonEntity):
    """Button to reset the service reminder."""

    _attr_has_entity_name = True
    _attr_translation_key = "reset_service_reminder"
    _attr_icon = "mdi:restart-alert"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator.coordinator)

        self._coordinator = coordinator
        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_reset_service_reminder"
        self.entity_id = build_entity_id("button", entry, "reset_service_reminder")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return build_device_info(self._entry)

    async def async_press(self) -> None:
        """Reset the service reminder."""
        result = await self.hass.async_add_executor_job(
            self._coordinator.reset_service_reminder
        )

        if not result:
            raise HomeAssistantError("Failed to reset service reminder.")