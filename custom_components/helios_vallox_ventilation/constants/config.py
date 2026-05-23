# Config keys for house / ventilation model
CONF_HOUSE_AREA = "house_area"
CONF_HOUSE_VOLUME = "house_volume"
CONF_ISOLATION_FACTOR = "isolation_factor"
CONF_AIRFLOW_PER_MODE = "airflow_per_mode"
CONF_MAX_AIRFLOW = "max_airflow"
CONF_POWER_PER_MODE = "power_per_mode"
CONF_MAX_POWER = "max_power"
CONF_HEATING_POWER = "heating_power"
CONF_DEVICE_MODEL = "device_model"

CUSTOM_MODEL = "Custom / None"

# Predefined device profiles
DEVICE_PRESETS = {
    "Vallox 90 SE": {
        CONF_AIRFLOW_PER_MODE: "43,86,107,129,158,187,231,276",
        CONF_MAX_AIRFLOW: 509,
        CONF_POWER_PER_MODE: "12,18,25,34,50,75,117,185",
        CONF_MAX_POWER: 185,
        CONF_HEATING_POWER: 900,
    },
    "Helios EC300 Pro": {
        CONF_AIRFLOW_PER_MODE: "105,165,195,240,270,305,335,360",
        CONF_MAX_AIRFLOW: 360,
        CONF_POWER_PER_MODE: "20,36,50,72,92,130,160,194",
        CONF_MAX_POWER: 194,
        CONF_HEATING_POWER: 1000,
    },
}
