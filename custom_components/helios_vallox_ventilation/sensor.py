import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .device_info import build_device_info, build_suggested_object_id
from .constants import DOMAIN, SENSOR_ENTITIES

_LOGGER = logging.getLogger("helios_vallox.sensor")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        HeliosSensor(coordinator, entry, sensor_def)
        for sensor_def in SENSOR_ENTITIES
    ]
    async_add_entities(entities)


class HeliosSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, sensor_def):
        super().__init__(coordinator.coordinator)
        self._coordinator = coordinator
        self._variable = sensor_def["key"]
        self._attr_translation_key = sensor_def["key"]
        self._attr_unique_id = f"{entry.entry_id}_{sensor_def['key']}"
        self._attr_native_unit_of_measurement = sensor_def.get("unit")
        self._attr_device_class = sensor_def.get("device_class")
        self._attr_state_class = sensor_def.get("state_class")
        self._attr_icon = sensor_def.get("icon")
        if sensor_def.get("device_class") == "enum":
            self._attr_options = sensor_def.get("options", [])
        self._attr_entity_registry_enabled_default = sensor_def.get("enabled_default", True)
        self._description = sensor_def.get("description")
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return build_device_info(self._entry)

    @property
    def suggested_object_id(self) -> str:
        """Return a stable English object id for the entity registry."""
        return build_suggested_object_id(self._entry, self._variable)

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._variable)

    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._description:
            attrs["description"] = self._description
        return attrs if attrs else None
