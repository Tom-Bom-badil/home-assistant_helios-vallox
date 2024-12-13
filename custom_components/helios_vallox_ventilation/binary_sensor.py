from homeassistant.components.binary_sensor import BinarySensorEntity
from custom_components.helios_vallox_ventilation import HeliosData
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up Helios Pro / Vallox SE binary sensors."""
    data_provider = HeliosData()
    data_provider.update()

    binary_sensor_config = discovery_info.get("binary_sensors", []) if discovery_info else []
    binary_sensors = []

    for sensor in binary_sensor_config:
        name = sensor.get("name")
        if not name:
            continue
        binary_sensors.append(
            HeliosBinarySensor(
                name=name,
                variable=name,
                data_provider=data_provider,
                device_class=sensor.get("device_class"),
                icon=sensor.get("icon")
            )
        )
    async_add_entities(binary_sensors)
    hass.data.setdefault("ventilation_entities", []).extend(binary_sensors)
    _LOGGER.info("Helios Pro / Vallox SE binary sensors successfully set up.")

class HeliosBinarySensor(BinarySensorEntity):
    """Representation of a Helios Pro / Vallox SE Binary Sensor."""

    def __init__(self, name, variable, data_provider, device_class=None, icon=None):
        self._name = f"ventilation_{name}"
        self._variable = variable
        self._state = None
        self._device_class = device_class
        self._icon = icon
        self._data_provider = data_provider

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return bool(self._data_provider.get_value(self._variable))

    @property
    def device_class(self):
        return self._device_class

    @property
    def icon(self):
        return self._icon

    def update(self):
        value = self._data_provider.get_value(self._variable)
        self._state = bool(value)
