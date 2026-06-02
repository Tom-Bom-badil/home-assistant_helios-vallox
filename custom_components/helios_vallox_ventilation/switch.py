import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .constants import DOMAIN, SWITCH_ENTITIES, SOFTBOOST_SWITCH_ENTITIES
from .device_info import build_device_info, build_entity_id


_LOGGER = logging.getLogger("helios_vallox.switch")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        HeliosSwitch(coordinator, entry, switch_def)
        for switch_def in SWITCH_ENTITIES
    ]
    # Per-device Softboost switches.
    # These do not write directly to the ventilation unit.
    entities.extend(
        HeliosSoftBoostSwitch(coordinator, entry, switch_def)
        for switch_def in SOFTBOOST_SWITCH_ENTITIES
    )
    async_add_entities(entities)


class HeliosSwitch(CoordinatorEntity, SwitchEntity):

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, switch_def):
        super().__init__(coordinator.coordinator)
        self._coordinator = coordinator
        self._variable = switch_def["key"]
        self._attr_translation_key = switch_def["key"]
        self._attr_unique_id = f"{entry.entry_id}_{switch_def['key']}"
        self.entity_id = build_entity_id("switch", entry, switch_def["key"])
        self._attr_icon = switch_def.get("icon")
        self._attr_entity_registry_enabled_default = switch_def.get("enabled_default", True)
        entity_category = switch_def.get("entity_category")
        if entity_category:
            self._attr_entity_category = EntityCategory(entity_category)
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return build_device_info(self._entry)

    @property
    def is_on(self):
        if self.coordinator.data is None:
            return None
        return bool(self.coordinator.data.get(self._variable))

    async def async_turn_on(self, **kwargs):
        await self._coordinator.turn_on(self._variable)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._coordinator.turn_off(self._variable)
        self.async_write_ha_state()


class HeliosSoftBoostSwitch(CoordinatorEntity, SwitchEntity):
    """Local per-device Softboost switch without direct bus access."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, entry, switch_def):
        super().__init__(coordinator.coordinator)
        self._coordinator = coordinator
        self._entry = entry
        self._variable = switch_def["key"]

        self._attr_translation_key = self._variable
        self._attr_unique_id = f"{entry.entry_id}_{self._variable}"
        self.entity_id = build_entity_id("switch", entry, self._variable)
        self._attr_icon = switch_def.get("icon")

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
    def is_on(self):
        """Return current local Softboost switch state."""
        softboost = self._coordinator.softboost
        if self._variable == "softboost_fireplace_mode":
            return softboost.state.fireplace_mode
        if self._variable == "softboost_active":
            return softboost.is_active
        return False

    async def async_turn_on(self, **kwargs):
        """Turn on local Softboost option or start Softboost."""
        softboost = self._coordinator.softboost
        if self._variable == "softboost_fireplace_mode":
            softboost.state.fireplace_mode = True
            await softboost.async_save()
            self.async_write_ha_state()
            return
        if self._variable == "softboost_active":
            await softboost.async_start()
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn off local Softboost option or stop Softboost."""
        softboost = self._coordinator.softboost
        if self._variable == "softboost_fireplace_mode":
            softboost.state.fireplace_mode = False
            await softboost.async_save()
            self.async_write_ha_state()
            return
        if self._variable == "softboost_active":
            await softboost.async_stop()
            self.async_write_ha_state()