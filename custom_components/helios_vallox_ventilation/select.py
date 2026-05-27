import logging
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify
from .device_info import (
    build_device_info,
    build_entity_id,
    get_localized_entity_name,
    get_entity_prefix,
)
from .constants import (
    DOMAIN,
    SELECT_ENTITIES,
    LOVELACE_DEVICE_SELECT_KEY,
    LOVELACE_DEVICE_SELECT_NAME,
    LOVELACE_DEVICE_SELECT_UNIQUE_ID,
    LOVELACE_DEVICE_SELECT_OBJECT_ID,
)


_LOGGER = logging.getLogger("helios_vallox.select")


def _build_lovelace_devices(hass: HomeAssistant) -> list[dict[str, str]]:
    """Build available ventilation devices from config entries."""
    devices: list[dict[str, str]] = []

    for entry in hass.config_entries.async_entries(DOMAIN):
        label = get_entity_prefix(entry)
        slug = slugify(label)

        if not slug:
            continue

        devices.append(
            {
                "label": label,
                "slug": slug,
                "entry_id": entry.entry_id,
            }
        )

    devices.sort(key=lambda item: item["label"].lower())
    return devices


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:

    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SelectEntity] = [
        HeliosSelect(coordinator, entry, select_def)
        for select_def in SELECT_ENTITIES
    ]

    dashboard_select = hass.data[DOMAIN].get(LOVELACE_DEVICE_SELECT_KEY)

    if dashboard_select is None:
        dashboard_select = Helios_Vallox_UI_Select(hass)
        hass.data[DOMAIN][LOVELACE_DEVICE_SELECT_KEY] = dashboard_select
        entities.append(dashboard_select)
    else:
        dashboard_select.async_refresh_devices()

    async_add_entities(entities)


class Helios_Vallox_UI_Select(RestoreEntity, SelectEntity):
    """Global ventilation selector for Lovelace dashboards."""

    _attr_has_entity_name = False
    _attr_name = LOVELACE_DEVICE_SELECT_NAME
    _attr_unique_id = LOVELACE_DEVICE_SELECT_UNIQUE_ID
    _attr_suggested_object_id = LOVELACE_DEVICE_SELECT_OBJECT_ID
    _attr_icon = "mdi:fan"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._selected_slug: str | None = None

    async def async_added_to_hass(self) -> None:
        """Restore previous selection."""
        await super().async_added_to_hass()

        if last_state := await self.async_get_last_state():
            restored_slug = last_state.attributes.get("selected_slug")
            if isinstance(restored_slug, str) and restored_slug:
                self._selected_slug = restored_slug

        self._ensure_valid_selection()

    async def async_will_remove_from_hass(self) -> None:
        """Clear reference when the device is removed."""
        if self.hass.data[DOMAIN].get(LOVELACE_DEVICE_SELECT_KEY) is self:
            self.hass.data[DOMAIN].pop(LOVELACE_DEVICE_SELECT_KEY, None)

    def async_refresh_devices(self) -> None:
        """Refresh state after config entry changes."""
        self._ensure_valid_selection()

        if getattr(self, "platform", None) is not None:
            self.async_write_ha_state()

    def _devices(self) -> list[dict[str, str]]:
        """Return current devices."""
        return _build_lovelace_devices(self.hass)

    def _device_by_slug(self, slug: str | None) -> dict[str, str] | None:
        """Find a device by slug."""
        if not slug:
            return None
        for device in self._devices():
            if device["slug"] == slug:
                return device
        return None

    def _device_by_label(self, label: str) -> dict[str, str] | None:
        """Find a device by label."""
        for device in self._devices():
            if device["label"] == label:
                return device
        return None

    def _ensure_valid_selection(self) -> None:
        """Ensure the selected device still exists."""
        if self._device_by_slug(self._selected_slug):
            return
        devices = self._devices()
        self._selected_slug = devices[0]["slug"] if devices else None

    @property
    def device_info(self) -> None:
        """Return no device information on startup.
        This is a global dashboard helper entity and does not belong
        to one specific ventilation device.
        """
        return None

    @property
    def options(self) -> list[str]:
        """Return available device labels."""
        return [device["label"] for device in self._devices()]

    @property
    def current_option(self) -> str | None:
        """Return selected device label."""
        selected = self._device_by_slug(self._selected_slug)
        return selected["label"] if selected else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return selected device metadata."""
        selected = self._device_by_slug(self._selected_slug)
        return {
            "selected_slug": selected["slug"] if selected else "",
            "entity_prefix": selected["slug"] if selected else "",
            "selected_entry_id": selected["entry_id"] if selected else "",
            "available_devices": self._devices(),
        }

    async def async_select_option(self, option: str) -> None:
        """Select a ventilation device."""
        selected = self._device_by_label(option)
        if selected is None:
            _LOGGER.warning("Invalid Lovelace device selection: %s", option)
            return
        self._selected_slug = selected["slug"]
        self.async_write_ha_state()


class HeliosSelect(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, select_def):
        super().__init__(coordinator.coordinator)
        self._coordinator = coordinator
        self._variable = select_def["key"]
        self._attr_translation_key = select_def["key"]
        self._attr_unique_id = f"{entry.entry_id}_{select_def['key']}"
        self.entity_id = build_entity_id("select", entry, select_def["key"])
        self._attr_icon = select_def.get("icon")
        self._attr_entity_registry_enabled_default = select_def.get("enabled_default", True)
        self._entry = entry
        # options mapping: raw int value -> display name
        self._value_to_name = select_def["options"]  # e.g. {0: "Fireplace", 1: "Normal"}
        self._name_to_value = {v: k for k, v in self._value_to_name.items()}
        self._attr_options = list(self._value_to_name.values())

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return build_device_info(self._entry)

    @property
    def name(self) -> str:
        """Return localized entity name without device prefix."""
        return get_localized_entity_name(self, "select", self._variable)

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
