import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .constants import DOMAIN, BINARY_SENSOR_ENTITIES, CONF_DEVICE_MODEL, CUSTOM_MODEL

_LOGGER = logging.getLogger("helios_vallox.binary_sensor")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        HeliosBinarySensor(coordinator, entry, sensor_def)
        for sensor_def in BINARY_SENSOR_ENTITIES
    ]
    async_add_entities(entities)


class HeliosBinarySensor(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, sensor_def):
        super().__init__(coordinator.coordinator)
        self._coordinator = coordinator
        self._variable = sensor_def["key"]
        self._attr_name = sensor_def["key"]
        self._attr_unique_id = f"{entry.entry_id}_{sensor_def['key']}"
        self._attr_device_class = sensor_def.get("device_class")
        self._attr_icon = sensor_def.get("icon")
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
