from homeassistant.components.sensor import SensorEntity
from custom_components.helios_vallox_ventilation import HELIOS_DATA
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up Helios Pro / Vallox SE sensors."""
    HELIOS_DATA.update()  # Aktualisiere die Daten
    sensor_config = discovery_info.get("sensors", []) if discovery_info else []
    sensors = []

    for sensor in sensor_config:
        name = sensor.get("name")
        if not name:
            continue
        sensors.append(
            HeliosSensor(
                name=name,
                variable=name,
                data_provider=HELIOS_DATA,
                unit_of_measurement=sensor.get("unit_of_measurement"),
                device_class=sensor.get("device_class"),
                icon=sensor.get("icon"),
                min_value=sensor.get("min_value"),
                max_value=sensor.get("max_value"),
                default_value=sensor.get("default_value"),
            )
        )
    async_add_entities(sensors)
    hass.data.setdefault("ventilation_entities", []).extend(sensors)
    _LOGGER.info("Helios Pro / Vallox SE sensors successfully set up.")

class HeliosSensor(SensorEntity):
    """Representation of a Helios Pro / Vallox SE Sensor."""

    def __init__(
        self,
        name,
        variable,
        data_provider,
        unit_of_measurement=None,
        device_class=None,
        icon=None,
        min_value=None,
        max_value=None,
        default_value=None,
    ):
        self._name = f"ventilation_{name}"
        self._variable = variable
        self._state = None
        self._unit_of_measurement = unit_of_measurement
        self._device_class = device_class
        self._icon = icon
        self._min_value = min_value
        self._max_value = max_value
        self._default_value = default_value
        self._data_provider = data_provider

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement

    @property
    def device_class(self):
        return self._device_class

    @property
    def icon(self):
        return self._icon

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attributes = {}
        if self._min_value is not None:
            attributes["min_value"] = self._min_value
        if self._max_value is not None:
            attributes["max_value"] = self._max_value
        if self._default_value is not None:
            attributes["default_value"] = self._default_value
        return attributes

    def update(self):
        value = self._data_provider.get_value(self._variable)
        self._state = value
