import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .constants import DOMAIN, SWITCH_ENTITIES, CONF_DEVICE_MODEL, CUSTOM_MODEL

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
    async_add_entities(entities)


class HeliosSwitch(CoordinatorEntity, SwitchEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, switch_def):
        super().__init__(coordinator.coordinator)
        self._coordinator = coordinator
        self._variable = switch_def["key"]
        self._attr_name = switch_def["key"]
        self._attr_unique_id = f"{entry.entry_id}_{switch_def['key']}"
        self._attr_icon = switch_def.get("icon")
        self._attr_entity_registry_enabled_default = switch_def.get("enabled_default", True)
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        model = self._entry.data.get(CONF_DEVICE_MODEL, CUSTOM_MODEL)
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=f"{model} Ventilation",
            manufacturer="Helios/Vallox",
            model=model,
        )

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
