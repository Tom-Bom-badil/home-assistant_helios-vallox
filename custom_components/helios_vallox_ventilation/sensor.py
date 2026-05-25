import logging
from typing import Any
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify
from .constants import DOMAIN, SENSOR_ENTITIES
from .constants.config import (
    CONF_AIRFLOW_PER_MODE,
    CONF_DEVICE_MODEL,
    CONF_ENTITY_PREFIX,
    CONF_HEATING_POWER,
    CONF_HOUSE_AREA,
    CONF_HOUSE_VOLUME,
    CONF_ISOLATION_FACTOR,
    CONF_MAX_AIRFLOW,
    CONF_MAX_POWER,
    CONF_POWER_PER_MODE,
    CUSTOM_MODEL,
    DEFAULT_ENTITY_PREFIX,
)
from .device_info import (
    build_device_info,
    build_entity_id,
    get_entity_prefix,
    get_localized_entity_name,
)


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
    entities.append(HeliosConfigurationSensor(entry))
    async_add_entities(entities)


class HeliosSensor(CoordinatorEntity, SensorEntity):

    _attr_has_entity_name = False

    def __init__(self, coordinator, entry, sensor_def):
        super().__init__(coordinator.coordinator)
        self._coordinator = coordinator
        self._variable = sensor_def["key"]
        self._attr_translation_key = sensor_def["key"]
        self._attr_unique_id = f"{entry.entry_id}_{sensor_def['key']}"
        self.entity_id = build_entity_id("sensor", entry, sensor_def["key"])
        self._attr_native_unit_of_measurement = sensor_def.get("unit")
        self._attr_device_class = sensor_def.get("device_class")
        self._attr_state_class = sensor_def.get("state_class")
        self._attr_icon = sensor_def.get("icon")
        if sensor_def.get("device_class") == "enum":
            self._attr_options = sensor_def.get("options", [])
        self._attr_entity_registry_enabled_default = sensor_def.get(
            "enabled_default", True
        )
        self._description = sensor_def.get("description")
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return build_device_info(self._entry)

    @property
    def name(self) -> str:
        """Return localized entity name without device prefix."""
        return get_localized_entity_name(self, "sensor", self._variable)

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


class HeliosConfigurationSensor(SensorEntity):
    """Expose static configuration values for dashboards/templates."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_icon = "mdi:cog"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._variable = "configuration"

        self._attr_translation_key = self._variable
        self._attr_unique_id = f"{entry.entry_id}_{self._variable}"
        self.entity_id = build_entity_id("sensor", entry, self._variable)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return build_device_info(self._entry)

    @property
    def name(self) -> str:
        """Return localized entity name without device prefix."""
        return get_localized_entity_name(self, "sensor", self._variable)

    @property
    def native_value(self) -> str:
        """Return a stable state for the configuration sensor."""
        return "configured"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return configuration values as dashboard-friendly attributes."""

        airflow_per_mode = self._csv_to_int_list(
            self._get_entry_value(CONF_AIRFLOW_PER_MODE)
        )
        power_per_mode = self._csv_to_int_list(
            self._get_entry_value(CONF_POWER_PER_MODE)
        )
        entity_prefix = self._get_entry_value(
            CONF_ENTITY_PREFIX,
            DEFAULT_ENTITY_PREFIX,
        )

        return {
            "registry_entry_id": self._entry.entry_id,
            "unique_device_name": entity_prefix,
            "unique_entity_prefix": f"{slugify(entity_prefix)}_",
            "device_model": self._get_entry_value(
                CONF_DEVICE_MODEL,
                CUSTOM_MODEL,
            ),
            "house_area": self._as_float_or_none(
                self._get_entry_value(CONF_HOUSE_AREA)
            ),
            "house_volume": self._as_float_or_none(
                self._get_entry_value(CONF_HOUSE_VOLUME)
            ),
            "isolation_factor": self._as_float_or_none(
                self._get_entry_value(CONF_ISOLATION_FACTOR)
            ),
            "airflow_per_mode": airflow_per_mode,
            "max_airflow": self._as_int_or_none(
                self._get_entry_value(CONF_MAX_AIRFLOW)
            ),
            "power_per_mode": power_per_mode,
            "max_power": self._as_int_or_none(
                self._get_entry_value(CONF_MAX_POWER)
            ),
            "heating_power": self._as_int_or_none(
                self._get_entry_value(CONF_HEATING_POWER)
            ),
        }

    def _get_entry_value(self, key: str, default: Any = None) -> Any:
        """Return a value from options first, then data."""
        return self._entry.options.get(
            key,
            self._entry.data.get(key, default),
        )

    @staticmethod
    def _csv_to_int_list(value: Any) -> list[int]:
        """Convert a CSV string or list to a list of integers.

        The config flow stores airflow_per_mode and power_per_mode with
        a leading 0 for fan speed 0. If older data still contains only
        the 8 real fan levels, prepend the 0 here for dashboard safety.
        """
        if value in (None, ""):
            return []

        if isinstance(value, list):
            raw_values = value
        else:
            raw_values = str(value).split(",")

        result: list[int] = []

        for item in raw_values:
            item = str(item).strip()
            if not item:
                continue

            try:
                result.append(int(item))
            except ValueError:
                _LOGGER.warning(
                    "Invalid integer value in configuration list: %s",
                    item,
                )

        if len(result) == 8:
            return [0, *result]

        return result

    @staticmethod
    def _as_int_or_none(value: Any) -> int | None:
        """Convert a value to int or None."""
        if value in (None, ""):
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_float_or_none(value: Any) -> float | None:
        """Convert a value to float or None."""
        if value in (None, ""):
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None
