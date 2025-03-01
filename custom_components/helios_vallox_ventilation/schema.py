import voluptuous as vol
from homeassistant.const import CONF_IP_ADDRESS, CONF_PORT
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN

# Configuration schema
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_IP_ADDRESS): cv.string,
                vol.Required(CONF_PORT): cv.port,
                vol.Optional("sensors", default=[]): vol.All(
                    cv.ensure_list,
                    [
                        vol.Schema(
                            {
                                vol.Required("name"): cv.string,
                                vol.Optional("description"): cv.string,
                                vol.Optional("unit_of_measurement"): cv.string,
                                vol.Optional("device_class"): cv.string,
                                vol.Optional("state_class"): cv.string,
                                vol.Optional("min_value"): vol.Coerce(float),
                                vol.Optional("max_value"): vol.Coerce(float),
                                vol.Optional("factory_setting"): vol.Coerce(float),
                                vol.Optional("icon"): cv.icon,
                            }
                        )
                    ],
                ),
                vol.Optional("binary_sensors", default=[]): vol.All(
                    cv.ensure_list,
                    [
                        vol.Schema(
                            {
                                vol.Required("name"): cv.string,
                                vol.Optional("description"): cv.string,
                                vol.Optional("device_class"): cv.string,
                                vol.Optional("icon"): cv.icon,
                            }
                        )
                    ],
                ),
                vol.Optional("switches", default=[]): vol.All(
                    cv.ensure_list,
                    [
                        vol.Schema(
                            {
                                vol.Required("name"): cv.string,
                                vol.Optional("description"): cv.string,
                                vol.Optional("device_class"): cv.string,
                                vol.Optional("icon"): cv.icon,
                            }
                        )
                    ],
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

# Service schema
SERVICE_WRITE_VALUE_SCHEMA = vol.Schema({
    vol.Required("variable"): cv.string,
    vol.Required("value"): vol.Coerce(int),
})
