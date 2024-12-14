from homeassistant.core import ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta
import voluptuous as vol
import logging
import subprocess
import json


_LOGGER = logging.getLogger(__name__)


# Schema
SERVICE_WRITE_VALUE_SCHEMA = vol.Schema({
    vol.Required("variable"): cv.string,
    vol.Required("value"): vol.Coerce(int),
})


# Shared class - fetch and cache data from the python script
class HeliosData:

    def __init__(self, config):
        self.data = None
        self.ip_address = config.get("ip_address", "192.168.178.38")
        self.port = config.get("port", 8234)
        _LOGGER.debug(f"Initialized HeliosData with IP: {self.ip_address} and Port: {self.port}")


    # fetch and cache
    def update(self):
        try:
            # ["python3", "/config/scripts/helios_vallox_ventilation.py", "--json"],
            result = subprocess.run(
                [
                    "python3", "/config/scripts/helios_vallox_ventilation.py",
                    "--json",
                    "--ip", self.ip_address,
                    "--port", str(self.port),
                ],
                capture_output=True,
                text=True,
                check=True
            )
            self.data = json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            _LOGGER.error(f"Helios script error: {e.stderr}")
            self.data = None
        except Exception as e:
            _LOGGER.error(f"Unexpected error reading Helios data: {e}")
            self.data = None

    # return value for a specific variable
    def get_value(self, variable):
        if self.data:
            return self.data.get(variable, None)
        return None


# HELIOS_DATA = HeliosData()


# write a specific variable to ventilation
def write_value(variable: str, value: int) -> bool:

    try:
        _LOGGER.debug(f"Writing {value} to variable {variable}")
        ip_address = HELIOS_DATA.ip_address
        port = HELIOS_DATA.port
        result = subprocess.run(
            [
                "python3", "/config/scripts/helios_vallox_ventilation.py",
                "--write_value", variable, str(value),
                "--ip", ip_address,
                "--port", str(port),
            ],
            capture_output=True,
            text=True,
            check=True
        )
        if result.returncode == 0:
            _LOGGER.debug(f"Successfully wrote {value} to {variable}")
            
            # refresh cache
            if HELIOS_DATA.data is None:
                HELIOS_DATA.data = {}
            HELIOS_DATA.data[variable] = value

            return True
        else:
            _LOGGER.error(f"Failed to write {value} to {variable}: {result.stderr}")
            return False

    except Exception as e:
        _LOGGER.error(f"Error writing to ventilation system: {e}", exc_info=True)
        return False


# get all valid variables from cache
def get_valid_variables():

    if HELIOS_DATA.data:
        return list(HELIOS_DATA.data.keys())
    # fallback, just in case cache is empty for some reason
    _LOGGER.warning("HELIOS_DATA cache is empty; using fallback variables.")
    return ["powerstate", "fanspeed"]


# create the write service handler
def create_write_service_handler(hass):

    # handle the write_value service
    async def handle_write_service(call: ServiceCall):

        _LOGGER.debug(f"Handling write_value service call: {call.data}")
        try:
            variable = call.data.get("variable")
            value = call.data.get("value")
            
            # valid call?
            if not variable or value is None:
                _LOGGER.error("Missing 'variable' or 'value' in service call data")
                return

            # known variable?
            valid_variables = get_valid_variables()
            if variable not in valid_variables:
                _LOGGER.error(f"Invalid variable: {variable}")
                return

            # bool incoming as text?
            if str(value).lower() in ["on", "an", "true"]:
                value = 1
            elif str(value).lower() in ["off", "aus", "false"]:
                value = 0

            # int for value?
            try:
                value = int(value)
            except ValueError:
                _LOGGER.error(f"Invalid value: {value} - not a number or bool.")
                return

            # check for extended attributes
            for entity in hass.data.get("ventilation_entities", []):
                if entity.name == variable:

                    # read-only variable?
                    if getattr(entity, "state_class", None) == "measurement":
                        _LOGGER.error(f"Attempt to write to read-only variable: {variable}")
                        return

                    # outside min_value .. max_value?
                    min_value = getattr(entity, "min_value", None)
                    max_value = getattr(entity, "max_value", None)

                    if min_value is not None and value < min_value:
                        _LOGGER.error(f"Value {value} is below min_value {min_value} for variable: {variable}")
                        return

                    if max_value is not None and value > max_value:
                        _LOGGER.error(f"Value {value} is above max_value {max_value} for variable: {variable}")
                        return

            # write it by using hass.async_add_executor_job
            _LOGGER.debug(f"Attempting to write {value} to {variable}")
            success = await hass.async_add_executor_job(write_value, variable, value)

            if success:
                _LOGGER.debug(f"Successfully wrote {value} to {variable}")

                # update entity
                for entity in hass.data.get("ventilation_entities", []):
                    if entity.name == variable:
                        entity.async_schedule_update_ha_state(force_refresh=True)

            else:
                _LOGGER.error(f"Failed to write {value} to {variable}")

        except Exception as e:
            _LOGGER.error(f"Error in handle_write_service: {e}", exc_info=True)

    return handle_write_service


# set up the integration
async def async_setup(hass, config):

    _LOGGER.debug("Starting setup of Helios Pro / Vallox SE Integration")
    try:
        # ventilation_config = config.get("helios_vallox_ventilation")
        ventilation_config = config.get("helios_vallox_ventilation", {})
        if not ventilation_config:
            _LOGGER.error("No configuration found for Helios Pro / Vallox SE.")
            return False

        global HELIOS_DATA
        HELIOS_DATA = HeliosData(ventilation_config)

        # IP adress and port for writing
        ip_address = ventilation_config.get("ip_address", "192.168.178.38")
        port = ventilation_config.get("port", 8234)

        _LOGGER.debug(f"Loaded configuration: {ventilation_config}")

        # load platforms for entities
        hass.async_create_task(
            async_load_platform(hass, "sensor", "helios_vallox_ventilation", {"sensors": ventilation_config.get("sensors", [])}, config)
        )
        hass.async_create_task(
            async_load_platform(hass, "binary_sensor", "helios_vallox_ventilation", {"binary_sensors": ventilation_config.get("binary_sensors", [])}, config)
        )
        hass.async_create_task(
            async_load_platform(hass, "switch", "helios_vallox_ventilation", {"switches": ventilation_config.get("switches", [])}, config)
        )

        # refresh entities in regular intervals
        async def update_data(_):
            _LOGGER.debug("Updating Helios data")
            HELIOS_DATA.update()

        # set the interval
        async_track_time_interval(hass, update_data, timedelta(minutes=1))

        # register write service
        try:
            hass.services.async_register(
                "helios_vallox_ventilation",
                "write_value",
                create_write_service_handler(hass),
                schema=SERVICE_WRITE_VALUE_SCHEMA
            )
            _LOGGER.debug("Service write_value registered successfully")
            
        except Exception as e:
            _LOGGER.error(f"Failed to register service write_value: {e}", exc_info=True)
            return False

        _LOGGER.debug("Helios Pro / Vallox SE Integration setup completed successfully")
        return True
        
    except Exception as e:
        _LOGGER.error(f"Error during setup: {e}", exc_info=True)
        return False
