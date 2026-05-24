import logging
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .device_info import build_device_info, build_suggested_object_id
from .constants import DOMAIN, NUMBER_ENTITIES

_LOGGER = logging.getLogger("helios_vallox.number")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        HeliosNumber(coordinator, entry, number_def)
        for number_def in NUMBER_ENTITIES
    ]
    async_add_entities(entities)


class HeliosNumber(CoordinatorEntity, NumberEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, number_def):
        super().__init__(coordinator.coordinator)
        self._coordinator = coordinator
        self._variable = number_def["key"]
        self._attr_translation_key = number_def["key"]
        self._attr_unique_id = f"{entry.entry_id}_{number_def['key']}"
        self._attr_native_unit_of_measurement = number_def.get("unit")
        self._attr_native_min_value = number_def.get("min", 0)
        self._attr_native_max_value = number_def.get("max", 255)
        self._attr_native_step = number_def.get("step", 1)
        self._attr_icon = number_def.get("icon")
        self._attr_mode = NumberMode.SLIDER if number_def.get("mode") == "slider" else NumberMode.BOX
        self._attr_entity_registry_enabled_default = number_def.get("enabled_default", True)
        self._description = number_def.get("description")
        self._factory_setting = number_def.get("factory_setting")
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

    async def async_set_native_value(self, value: float) -> None:
        int_value = int(value)
        await self.hass.async_add_executor_job(
            self._coordinator.write_value, self._variable, int_value,
            self._attr_native_min_value, self._attr_native_max_value
        )
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._factory_setting is not None:
            attrs["factory_setting"] = self._factory_setting
        if self._description:
            attrs["description"] = self._description
        return attrs if attrs else None
