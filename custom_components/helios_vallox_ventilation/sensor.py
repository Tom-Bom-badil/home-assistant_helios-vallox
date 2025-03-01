import logging
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN

# _LOGGER = logging.getLogger(__name__)
_LOGGER = logging.getLogger("helios_vallox.sensor")

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
                icon=sensor.get("icon"),
                unique_id=f"ventilation_{name}",
                description=sensor.get("description"),
                unit_of_measurement=sensor.get("unit_of_measurement"),
                device_class=sensor.get("device_class"),
                state_class=sensor.get("state_class"),
                min_value=sensor.get("min_value"),
                max_value=sensor.get("max_value"),
                factory_setting=sensor.get("factory_setting"),
            )
        )
    async_add_entities(entities)
    hass.data.setdefault("ventilation_entities", []).extend(entities)

# sensor class
class HeliosSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        name,
        variable,
        coordinator,
        icon=None,
        unique_id=None,
        description=None,
        unit_of_measurement=None,
        device_class=None,
        state_class=None,
        min_value=None,
        max_value=None,
        factory_setting=None,
    ):
        super().__init__(coordinator.coordinator)
        self._attr_name = f"Ventilation {name}"
        self._variable = variable
        self._coordinator = coordinator
        self._attr_icon = icon
        self._attr_unique_id = unique_id
        self._attr_description = description
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_min_value = min_value
        self._attr_max_value = max_value
        self._attr_factory_setting = factory_setting

    @property
    def native_value(self):
        return self.coordinator.data.get(self._variable)

    # additional state attributes
    @property
    def extra_state_attributes(self):
        attributes = {
            "min_value": self._attr_min_value,
            "max_value": self._attr_max_value,
            "factory_setting": self._attr_factory_setting,
            "description": self._attr_description,
        }
        return {k: v for k, v in attributes.items() if v is not None}

    # add entity
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_write_ha_state()

    # update entity
    def _handle_coordinator_update(self):
        super()._handle_coordinator_update()
