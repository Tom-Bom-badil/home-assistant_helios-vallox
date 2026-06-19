import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .constants import DOMAIN, SOFTBOOST_BUTTON_ENTITIES
from .device_info import build_device_info, build_entity_id


_LOGGER = logging.getLogger("helios_vallox.button")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        HeliosResetServiceReminderButton(coordinator, entry),
    ]
    entities.extend(
        HeliosSoftBoostButton(coordinator, entry, button_def)
        for button_def in SOFTBOOST_BUTTON_ENTITIES
    )
    async_add_entities(entities)


class HeliosResetServiceReminderButton(CoordinatorEntity, ButtonEntity):
    """Local per-device reset button for the service reminder."""

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


class HeliosSoftBoostButton(CoordinatorEntity, ButtonEntity):
    """Local per-device Softboost start/stop action button."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, entry: ConfigEntry, button_def: dict) -> None:
        super().__init__(coordinator.coordinator)
        self._coordinator = coordinator
        self._entry = entry
        self._variable = button_def["key"]
        self._attr_translation_key = self._variable
        self._attr_unique_id = f"{entry.entry_id}_{self._variable}"
        self.entity_id = build_entity_id("button", entry, self._variable)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return build_device_info(self._entry)

    async def async_added_to_hass(self) -> None:
        """Register for Softboost state updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._coordinator.softboost.async_add_listener(self.schedule_update_ha_state)
        )

    @property
    def icon(self) -> str:
        """Return a dynamic icon depending on Softboost state."""
        if self._coordinator.softboost.is_active:
            return "mdi:stop-circle-outline"

        return "mdi:play-circle-outline"

    async def async_press(self) -> None:
        """Start or stop Softboost depending on current state."""
        softboost = self._coordinator.softboost

        if softboost.is_active:
            await softboost.async_stop()
            self.async_write_ha_state()
            return

        result = await softboost.async_start()
        if not result:
            raise HomeAssistantError("Failed to start Softboost.")

        self.async_write_ha_state()