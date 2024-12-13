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

# Schema für den Schreib-Service
SERVICE_WRITE_VALUE_SCHEMA = vol.Schema({
    vol.Required("variable"): cv.string,  # Erwartet einen String
    vol.Required("value"): vol.Coerce(int),  # Erwartet einen Integer (wird bei Bedarf konvertiert)
})


class HeliosData:
    """Shared class to fetch and cache data from the Helios Python script."""

    def __init__(self):
        self.data = None

    def update(self):
        """Fetch data from the Helios Python script."""
        try:
            result = subprocess.run(
                ["python3", "/config/scripts/helios_vallox_ventilation.py", "--json"],
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

    def get_value(self, variable):
        """Retrieve the value for a specific variable."""
        if self.data:
            return self.data.get(variable, None)
        return None


HELIOS_DATA = HeliosData()


def write_value(variable: str, value: int) -> bool:
    """Write a value to the ventilation system."""
    try:
        _LOGGER.info(f"Writing {value} to variable {variable}")
        result = subprocess.run(
            ["python3", "/config/scripts/helios_vallox_ventilation.py", "--write_value", variable, str(value)],
            capture_output=True,
            text=True,
            check=True
        )
        if result.returncode == 0:
            _LOGGER.info(f"Successfully wrote {value} to {variable}")
            
            # Aktualisiere HELIOS_DATA
            if HELIOS_DATA.data is None:
                HELIOS_DATA.data = {}
            HELIOS_DATA.data[variable] = value  # Aktualisiert den Wert im Cache

            return True
        else:
            _LOGGER.error(f"Failed to write {value} to {variable}: {result.stderr}")
            return False
    except Exception as e:
        _LOGGER.error(f"Error writing to ventilation system: {e}", exc_info=True)
        return False


def create_write_service_handler(hass):
    async def handle_write_service(call: ServiceCall):
        """Handle the write_value service."""
        _LOGGER.debug(f"Handling write_value service call: {call.data}")
        try:
            variable = call.data.get("variable")
            value = call.data.get("value")
            if not variable or value is None:
                _LOGGER.error("Missing 'variable' or 'value' in service call data")
                return
            valid_variables = ["fanspeed", "boost_mode", "preheat_setpoint"]
            if variable not in valid_variables:
                _LOGGER.error(f"Invalid variable: {variable}")
                return
            _LOGGER.info(f"Writing {value} to {variable}")
            # Verwende hass.async_add_executor_job
            success = await hass.async_add_executor_job(write_value, variable, value)
            if success:
                _LOGGER.info(f"Successfully wrote {value} to {variable}")
                # Benachrichtige die Entitäten
                for entity in hass.data.get("ventilation_entities", []):
                    if entity.name == variable:
                        entity.async_schedule_update_ha_state(force_refresh=True)
            else:
                _LOGGER.error(f"Failed to write {value} to {variable}")
        except Exception as e:
            _LOGGER.error(f"Error in handle_write_service: {e}", exc_info=True)
    return handle_write_service


async def async_setup(hass, config):
    """Set up the Helios Pro / Vallox SE Integration."""
    _LOGGER.debug("Starting setup of Helios Pro / Vallox SE Integration")
    try:
        ventilation_config = config.get("ventilation")
        if not ventilation_config:
            _LOGGER.error("No configuration found for Helios Pro / Vallox SE.")
            return False

        _LOGGER.debug(f"Loaded configuration: {ventilation_config}")

        # Plattformen laden
        hass.async_create_task(
            async_load_platform(hass, "sensor", "ventilation", {"sensors": ventilation_config.get("sensors", [])}, config)
        )
        hass.async_create_task(
            async_load_platform(hass, "binary_sensor", "ventilation", {"binary_sensors": ventilation_config.get("binary_sensors", [])}, config)
        )
        hass.async_create_task(
            async_load_platform(hass, "switch", "ventilation", {"switches": ventilation_config.get("switches", [])}, config)
        )

        # Funktion zur regelmäßigen Aktualisierung
        async def update_data(_):
            """Update Helios data periodically."""
            _LOGGER.debug("Updating Helios data")
            HELIOS_DATA.update()

        # Planung für jede Minute
        async_track_time_interval(hass, update_data, timedelta(minutes=1))

        # Schreib-Service registrieren
        try:
            hass.services.async_register(
                "ventilation",
                "write_value",
                create_write_service_handler(hass),  # Übergibt den hass-Kontext
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