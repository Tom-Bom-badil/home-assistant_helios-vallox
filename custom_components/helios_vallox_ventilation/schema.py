import voluptuous as vol
from homeassistant.helpers import config_validation as cv

# Service schema
SERVICE_WRITE_VALUE_SCHEMA = vol.Schema({
    vol.Optional("entry_id"): cv.string,
    vol.Required("variable"): cv.string,
    vol.Required("value"): vol.Coerce(int),
})
