import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .constants import DOMAIN, BINARY_SENSOR_ENTITIES
from .device_info import build_device_info, build_entity_id


_LOGGER = logging.getLogger("helios_vallox.binary_sensor")


INTERNAL_BINARY_SENSOR_KEYS = {
    "co2_sensor1_present",
    "co2_sensor2_present",
    "co2_sensor3_present",
    "co2_sensor4_present",
    "co2_sensor5_present",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:

    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        HeliosBinarySensor(coordinator, entry, sensor_def)
        for sensor_def in BINARY_SENSOR_ENTITIES
        if sensor_def["key"] not in INTERNAL_BINARY_SENSOR_KEYS
    ]
    async_add_entities(entities)


class HeliosBinarySensor(CoordinatorEntity, BinarySensorEntity):

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, sensor_def):
        super().__init__(coordinator.coordinator)
        self._coordinator = coordinator
        self._variable = sensor_def["key"]
        self._attr_translation_key = sensor_def["key"]
        self._attr_unique_id = f"{entry.entry_id}_{sensor_def['key']}"
        self.entity_id = build_entity_id("binary_sensor", entry, sensor_def["key"])
        self._attr_device_class = sensor_def.get("device_class")
        self._attr_icon = sensor_def.get("icon")
        self._attr_entity_registry_enabled_default = sensor_def.get("enabled_default", True)
        entity_category = sensor_def.get("entity_category")
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
