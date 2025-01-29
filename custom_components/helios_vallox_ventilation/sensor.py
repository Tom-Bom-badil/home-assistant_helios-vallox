import logging
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN
_LOGGER = logging.getLogger(__name__)


# platform setup
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    if discovery_info is None:
        return

    coordinator = hass.data[DOMAIN]["coordinator"]
    entities = []
    sensor_config = discovery_info.get("sensors", [])

    for sensor in sensor_config:
        name = sensor.get("name")
        if not name:
            _LOGGER.warning("Sensor configuration missing 'name'. Skipping entry.")
            continue
        entities.append(
            HeliosSensor(
                name=name,
                variable=name,
                coordinator=coordinator,
                description=sensor.get("description"),
                unit_of_measurement=sensor.get("unit_of_measurement"),
                device_class=sensor.get("device_class"),
                state_class=sensor.get("state_class"),
                icon=sensor.get("icon"),
                min_value=sensor.get("min_value"),
                max_value=sensor.get("max_value"),
                default_value=sensor.get("default_value"),
                unique_id=f"ventilation_{name}",
            )
        )

    async_add_entities(entities)
    hass.data.setdefault("ventilation_entities", []).extend(entities)
    _LOGGER.debug(f"Added {len(entities)} sensors for Helios/Vallox and registered it with coordinator {coordinator.coordinator}.")

# sensor class
class HeliosSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        name,
        variable,
        coordinator,
        description=None,
        unit_of_measurement=None,
        device_class=None,
        state_class=None,
        icon=None,
        min_value=None,
        max_value=None,
        default_value=None,
        unique_id=None,
    ):
        super().__init__(coordinator.coordinator)
        self._attr_name = f"Ventilation {name}"
        self._variable = variable
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_icon = icon
        self._attr_unique_id = unique_id
        self._description = description
        self._min_value = min_value
        self._max_value = max_value
        self._default_value = default_value
        # _LOGGER.debug(f"Registering sensor '{name}' with coordinator: {coordinator.coordinator}")

    @property
    def native_value(self):
        return self.coordinator.data.get(self._variable)

    # additional state attributes
    @property
    def extra_state_attributes(self):
        return {
            "min_value": self._min_value,
            "max_value": self._max_value,
            "default_value": self._default_value,
            "description": self._description,
        }

    # add entity
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_write_ha_state()

    # update entity
    def _handle_coordinator_update(self):
        super()._handle_coordinator_update()
