import logging
from datetime import datetime
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .constants import (
    BINARY_SENSOR_ENTITIES,
    DOMAIN,
    INTERNAL_BINARY_SENSOR_KEYS,
    SOFTBOOST_BINARY_SENSOR_ENTITIES,
)
from .device_info import build_device_info, build_entity_id

_LOGGER = logging.getLogger("helios_vallox.binary_sensor")

ATTR_LAST_RUN = "last_run"
ATTR_LAST_SUCCESSFUL_FULL_RUN = "last_successful_full_run"
ATTR_LAST_UNSUCCESSFUL_RUN = "last_unsuccessful_run"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        HeliosConnectionBinarySensor(coordinator, entry),
    ]

    entities.extend(
        HeliosBinarySensor(coordinator, entry, sensor_def)
        for sensor_def in BINARY_SENSOR_ENTITIES
        if sensor_def["key"] not in INTERNAL_BINARY_SENSOR_KEYS
    )

    entities.extend(
        HeliosSoftBoostBinarySensor(coordinator, entry, sensor_def)
        for sensor_def in SOFTBOOST_BINARY_SENSOR_ENTITIES
    )

    async_add_entities(entities)


class HeliosConnectionBinarySensor(BinarySensorEntity):
    """Show whether the latest completed full read was successful."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._data_coordinator = coordinator.coordinator
        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_connection"
        self.entity_id = build_entity_id(
            "binary_sensor",
            entry,
            "connection",
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return build_device_info(self._entry)

    @property
    def available(self) -> bool:
        """Keep the connection indicator available during failures."""
        return True

    @property
    def is_on(self) -> bool | None:
        """Return the result of the latest completed full read."""
        return self._data_coordinator.last_run_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return coordinator run timestamps as ISO datetimes."""
        return {
            ATTR_LAST_RUN: self._as_iso(
                self._data_coordinator.last_run
            ),
            ATTR_LAST_SUCCESSFUL_FULL_RUN: self._as_iso(
                self._data_coordinator.last_successful_full_run
            ),
            ATTR_LAST_UNSUCCESSFUL_RUN: self._as_iso(
                self._data_coordinator.last_unsuccessful_run
            ),
        }

    async def async_added_to_hass(self) -> None:
        """Register for every completed coordinator run."""
        await super().async_added_to_hass()

        self.async_on_remove(
            self._data_coordinator.async_add_run_finished_listener(
                self._handle_run_finished
            )
        )

    async def async_update(self) -> None:
        """Request a full coordinator refresh."""
        await self._data_coordinator.async_request_refresh()

    @callback
    def _handle_run_finished(self) -> None:
        """Write the new state after every completed run."""
        self.async_write_ha_state()

    @staticmethod
    def _as_iso(value: datetime | None) -> str | None:
        """Convert a datetime to an ISO-8601 string."""
        return value.isoformat() if value is not None else None


class HeliosBinarySensor(
    CoordinatorEntity,
    BinarySensorEntity,
):
    """Local per-device generic binary sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, sensor_def):
        super().__init__(coordinator.coordinator)

        self._coordinator = coordinator
        self._variable = sensor_def["key"]
        self._entry = entry

        self._attr_translation_key = sensor_def["key"]
        self._attr_unique_id = (
            f"{entry.entry_id}_{sensor_def['key']}"
        )
        self.entity_id = build_entity_id(
            "binary_sensor",
            entry,
            sensor_def["key"],
        )

        self._attr_device_class = sensor_def.get("device_class")
        self._attr_icon = sensor_def.get("icon")
        self._attr_entity_registry_enabled_default = sensor_def.get(
            "enabled_default",
            True,
        )

        entity_category = sensor_def.get("entity_category")
        if entity_category:
            self._attr_entity_category = EntityCategory(
                entity_category
            )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return build_device_info(self._entry)

    @property
    def is_on(self):
        """Return the binary register state."""
        if self.coordinator.data is None:
            return None

        return bool(
            self.coordinator.data.get(self._variable)
        )


class HeliosSoftBoostBinarySensor(
    CoordinatorEntity,
    BinarySensorEntity,
):
    """Local per-device Softboost status without direct bus access."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, entry, sensor_def):
        super().__init__(coordinator.coordinator)

        self._coordinator = coordinator
        self._entry = entry
        self._variable = sensor_def["key"]

        self._attr_translation_key = self._variable
        self._attr_unique_id = (
            f"{entry.entry_id}_{self._variable}"
        )
        self.entity_id = build_entity_id(
            "binary_sensor",
            entry,
            self._variable,
        )

        self._attr_icon = sensor_def.get("icon")

        entity_category = sensor_def.get("entity_category")
        if entity_category:
            self._attr_entity_category = EntityCategory(
                entity_category
            )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return build_device_info(self._entry)

    async def async_added_to_hass(self) -> None:
        """Register for Softboost state updates."""
        await super().async_added_to_hass()

        self.async_on_remove(
            self._coordinator.softboost.async_add_listener(
                self.schedule_update_ha_state
            )
        )

    @property
    def is_on(self):
        """Return the current local Softboost state."""
        if self._variable == "softboost_active":
            return self._coordinator.softboost.is_active

        return False
