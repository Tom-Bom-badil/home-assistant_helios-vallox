import logging
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .constants import DOMAIN, SELECT_ENTITIES, CONF_DEVICE_MODEL, CUSTOM_MODEL

_LOGGER = logging.getLogger("helios_vallox.select")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        HeliosSelect(coordinator, entry, select_def)
        for select_def in SELECT_ENTITIES
    ]
    async_add_entities(entities)


class HeliosSelect(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, select_def):
        super().__init__(coordinator.coordinator)
        self._coordinator = coordinator
        self._variable = select_def["key"]
        self._attr_translation_key = select_def["key"]
        self._attr_unique_id = f"{entry.entry_id}_{select_def['key']}"
        self._attr_icon = select_def.get("icon")
        self._attr_entity_registry_enabled_default = select_def.get("enabled_default", True)
        self._entry = entry
        # options mapping: raw int value -> display name
        self._value_to_name = select_def["options"]  # e.g. {0: "Fireplace", 1: "Normal"}
        self._name_to_value = {v: k for k, v in self._value_to_name.items()}
        self._attr_options = list(self._value_to_name.values())

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
    def current_option(self) -> str | None:
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._variable)
        if raw is None:
            return None
        return self._value_to_name.get(int(raw))

    async def async_select_option(self, option: str) -> None:
        value = self._name_to_value[option]
        await self.hass.async_add_executor_job(
            self._coordinator.write_value, self._variable, value
        )
        self.async_write_ha_state()
