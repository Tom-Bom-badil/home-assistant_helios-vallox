import logging
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .constants import DOMAIN, NUMBER_ENTITIES, UI_NUMBER_ENTITIES
from .device_info import (
    build_device_info,
    build_entity_id,
    get_localized_entity_name,
)


_LOGGER = logging.getLogger("helios_vallox.number")


CO2_NUMBER_KEYS = {
    "co2_setting_value",
}


def _should_create_number(coordinator, key: str) -> bool:
    """Return True if this number should be exposed as HA entity."""
    if key in CO2_NUMBER_KEYS:
        return coordinator.has_capability("co2")
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        HeliosNumber(coordinator, entry, number_def)
        for number_def in NUMBER_ENTITIES
        if _should_create_number(coordinator, number_def["key"])
    ]

    # Global UI/helper number entities. These are global dashboard state entities
    # and are not meant to be assigned to a specific ventilation device.
    for number_def in UI_NUMBER_ENTITIES:
        storage_key = number_def["storage_key"]
        existing_entity = hass.data[DOMAIN].get(storage_key)

        if existing_entity is None or getattr(existing_entity, "platform", None) is None:
            entity = Helios_Vallox_Ui_Numbers(number_def)
            hass.data[DOMAIN][storage_key] = entity
            entities.append(entity)

    async_add_entities(entities)


class HeliosNumber(CoordinatorEntity, NumberEntity):
    _attr_has_entity_name = False

    def __init__(self, coordinator, entry, number_def):
        super().__init__(coordinator.coordinator)
        self._coordinator = coordinator
        self._variable = number_def["key"]
        self._attr_translation_key = number_def["key"]
        self._attr_unique_id = f"{entry.entry_id}_{number_def['key']}"
        self.entity_id = build_entity_id("number", entry, number_def["key"])
        self._attr_native_unit_of_measurement = number_def.get("unit")
        self._attr_native_min_value = number_def.get("min", 0)
        self._attr_native_max_value = number_def.get("max", 255)
        self._attr_native_step = number_def.get("step", 1)
        self._attr_icon = number_def.get("icon")
        self._attr_mode = NumberMode.SLIDER if number_def.get("mode") == "slider" else NumberMode.BOX
        self._attr_entity_registry_enabled_default = number_def.get("enabled_default", True)
        self._description = number_def.get("description")
        self._factory_setting = number_def.get("factory_setting")
        entity_category = number_def.get("entity_category")
        if entity_category:
            self._attr_entity_category = EntityCategory(entity_category)
        self._entry = entry

    async def async_set_native_value(self, value: float) -> None:
        int_value = int(value)
        await self.hass.async_add_executor_job(
            self._coordinator.write_value,
            self._variable,
            int_value,
            self._attr_native_min_value,
            self._attr_native_max_value,
        )
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return build_device_info(self._entry)

    @property
    def name(self) -> str:
        """Return localized entity name without device prefix."""
        return get_localized_entity_name(self, "number", self._variable)

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._variable)

    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._factory_setting is not None:
            attrs["factory_setting"] = self._factory_setting
        if self._description:
            attrs["description"] = self._description
        return attrs if attrs else None


class Helios_Vallox_Ui_Numbers(RestoreEntity, NumberEntity):
    """Global UI/helper number entity without ventilation bus access."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, number_def: dict) -> None:
        self._attr_name = number_def["name"]
        self._attr_unique_id = number_def["unique_id"]
        self._attr_suggested_object_id = number_def["object_id"]

        self._attr_native_min_value = number_def["min"]
        self._attr_native_max_value = number_def["max"]
        self._attr_native_step = number_def["step"]
        self._attr_icon = number_def.get("icon")

        self._default_value = number_def["initial"]
        self._attr_native_value = self._default_value

    @property
    def device_info(self) -> None:
        """Return no device information.

        This is a global UI/helper entity and must not be assigned
        to one specific ventilation device.
        """
        return None

    async def async_added_to_hass(self) -> None:
        """Restore previous UI/helper value."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is None:
            return

        try:
            self._attr_native_value = self._normalize_value(last_state.state)
        except (TypeError, ValueError):
            self._attr_native_value = self._default_value

    async def async_set_native_value(self, value: float) -> None:
        """Set local UI/helper value.

        This intentionally does not write anything to the ventilation unit.
        """
        self._attr_native_value = self._normalize_value(value)
        self.async_write_ha_state()

    def _normalize_value(self, value) -> int:
        """Normalize and clamp the value to the configured range."""
        int_value = int(float(value))

        return max(
            int(self._attr_native_min_value),
            min(int(self._attr_native_max_value), int_value),
        )