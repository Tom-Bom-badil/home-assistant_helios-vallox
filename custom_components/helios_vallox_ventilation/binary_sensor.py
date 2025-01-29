import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
_LOGGER = logging.getLogger(__name__)

# platform setup
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    if discovery_info is None:
        return

    coordinator = hass.data[DOMAIN]["coordinator"]
    entities = []
    binary_sensor_config = discovery_info.get("binary_sensors", [])

    for sensor in binary_sensor_config:
        name = sensor.get("name")
        if not name:
            _LOGGER.warning("Binary sensor configuration missing 'name'. Skipping entry.")
            continue

        entities.append(
            HeliosBinarySensor(
                name=name,
                variable=name,
                coordinator=coordinator,
                description=sensor.get("description"),
                device_class=sensor.get("device_class"),
                icon=sensor.get("icon"),
                unique_id=f"ventilation_{name}",
            )
        )

    async_add_entities(entities)
    hass.data.setdefault("ventilation_entities", []).extend(entities)
    _LOGGER.debug(f"Added {len(entities)} binary sensors for Helios/Vallox and registered it with coordinator {coordinator.coordinator}.")


# binary_sensor class
class HeliosBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(
        self,
        name,
        variable,
        coordinator,
        description=None,
        device_class=None,
        icon=None,
        unique_id=None,
    ):
        super().__init__(coordinator.coordinator)
        self._attr_name = f"Ventilation {name}"
        self._variable = variable
        self._attr_description = description
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_unique_id = unique_id
        self._attr_is_on = None
        #_LOGGER.debug(f"Registering binary sensor '{name}' with coordinator: {coordinator.coordinator}")

    @property
    def is_on(self):
        return self.coordinator.data.get(self._variable)

    # additional state attributes
    @property
    def extra_state_attributes(self):
        attributes = {
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
