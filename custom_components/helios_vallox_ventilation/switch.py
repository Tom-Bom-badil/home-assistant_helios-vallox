from homeassistant.components.switch import SwitchEntity
from custom_components.helios_vallox_ventilation import HeliosData
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up Helios Pro / Vallox SE switches."""
    data_provider = HeliosData()
    data_provider.update()

    switches = [
        HeliosSwitch("boost_mode", data_provider),
        HeliosSwitch("power_state", data_provider)
    ]
    async_add_entities(switches)
    hass.data.setdefault("ventilation_entities", []).extend(switches)
    _LOGGER.info("Helios Pro / Vallox SE switches successfully set up.")

class HeliosSwitch(SwitchEntity):
    """Representation of a Helios Pro / Vallox SE switch."""

    def __init__(self, name, data_provider):
        self._name = f"ventilation_{name}"
        self._state = False
        self._data_provider = data_provider
        self._variable = name

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        """Return True if the switch is on."""
        return bool(self._data_provider.get_value(self._variable))

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.info(f"Turning on {self._name}")
        # Logik zum Aktivieren (z. B. durch ein Kommando an Helios)
        # Update self._state hier bei Erfolg
        self._state = True

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.info(f"Turning off {self._name}")
        # Logik zum Deaktivieren (z. B. durch ein Kommando an Helios)
        # Update self._state hier bei Erfolg
        self._state = False

    def update(self):
        """Fetch new state data for the switch."""
        self._state = bool(self._data_provider.get_value(self._variable))
