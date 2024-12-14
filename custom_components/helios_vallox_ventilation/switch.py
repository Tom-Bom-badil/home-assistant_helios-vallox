from homeassistant.components.switch import SwitchEntity
from custom_components.helios_vallox_ventilation import HELIOS_DATA
import logging


_LOGGER = logging.getLogger(__name__)


# set up switches
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):

    data_provider =     data_provider = HELIOS_DATA
    data_provider.update()

    switch_config = discovery_info.get("switches", []) if discovery_info else []
    switches = []

    for switch in switch_config:
        name = switch.get("name")
        if not name:
            continue
        switches.append(
            HeliosSwitch(
                name=name,
                variable=name,
                data_provider=data_provider,
                device_class=switch.get("device_class"),
                icon=switch.get("icon")
            )
        )
    async_add_entities(switches)
    hass.data.setdefault("ventilation_entities", []).extend(switches)
    _LOGGER.debug("Ventilation switches successfully set up.")


# representation of a switch
class HeliosSwitch(SwitchEntity):

    def __init__(self, name, variable, data_provider, device_class=None, icon=None):
        self._name = f"ventilation_{name}"
        self._variable = variable
        self._state = False
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

    # logic for activation
    def turn_on(self, **kwargs):
        _LOGGER.info(f"Turning on {self._name}")
        self._state = True

    # logic for de-activation
    def turn_off(self, **kwargs):
        _LOGGER.info(f"Turning off {self._name}")
        self._state = False

    def update(self):
        self._state = bool(self._data_provider.get_value(self._variable))
