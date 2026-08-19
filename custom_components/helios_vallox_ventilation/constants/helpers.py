###### UI / Dashboard helpers

# Device selector on the remote control of the example dashboard
LOVELACE_DEVICE_SELECT_KEY = "__helios_vallox_ui_device_select"
LOVELACE_DEVICE_SELECT_NAME = "Helios/Vallox UI Device Select"
LOVELACE_DEVICE_SELECT_UNIQUE_ID = "helios_vallox_ui_device_select"
LOVELACE_DEVICE_SELECT_OBJECT_ID = "helios_vallox_ui_device_select"

# Control entities for the remote control of the example dashboard
UI_NUMBER_ENTITIES = [
    {
        "storage_key": "__helios_vallox_ui_display_select",
        "name": "Helios/Vallox UI Display Select",
        "unique_id": "helios_vallox_ui_display_select",
        "object_id": "helios_vallox_ui_display_select",
        "initial": 1,
        "min": 1,
        "max": 3,
        "step": 1,
        "icon": "mdi:remote",
    },
    {
        "storage_key": "__helios_vallox_ui_display_index",
        "name": "Helios/Vallox UI Display Index",
        "unique_id": "helios_vallox_ui_display_index",
        "object_id": "helios_vallox_ui_display_index",
        "initial": 0,
        "min": 0,
        "max": 3,
        "step": 1,
        "icon": "mdi:remote",
    },
]


###### CO2 and rH

RH_SENSOR_KEYS = {
    "highest_humidity",
    "rh_sensor1",
    "rh_sensor2",
}

RH_NUMBER_KEYS = {
    "basic_humidity_level",
}

RH_SELECT_KEYS = {
    "humidity_control_mode",
}

CO2_NUMBER_KEYS = {
    "co2_setting_value",
}

CO2_SENSOR_KEYS = {
    "co2_concentration",
    "co2_setting_value",
}

INTERNAL_SENSOR_KEYS = {
    "rh_sensor1_raw",
    "rh_sensor2_raw",
    "co2_reading_upper_byte",
    "co2_reading_lower_byte",
    "co2_setting_upper_byte",
    "co2_setting_lower_byte",
}

INTERNAL_BINARY_SENSOR_KEYS = {
    "co2_sensor1_present",
    "co2_sensor2_present",
    "co2_sensor3_present",
    "co2_sensor4_present",
    "co2_sensor5_present",
}


###### Soft boost helpers

SOFTBOOST_STORAGE_VERSION = 1
SOFTBOOST_STORAGE_KEY_SUFFIX = "softboost"
# Default level
SOFTBOOST_DEFAULT_LEVEL = 8
# Default time (45 minutes)
SOFTBOOST_DEFAULT_DURATION = 45 * 60
# Fireplace only: Min softboost duration = 15 minutes; restore output fan before that
SOFTBOOST_FIREPLACE_RESTORE_DELAY = (15 * 60) - 5

SOFTBOOST_NUMBER_ENTITIES = [
    {"key": "softboost_level", "unit": None, "min": 1, "max": 8, "step": 1, "mode": "slider", "icon": "mdi:fan", "initial": SOFTBOOST_DEFAULT_LEVEL},
    {"key": "softboost_duration", "unit": "min", "min": 15, "max": 90, "step": 15, "mode": "box", "icon": "mdi:timer-outline", "initial": SOFTBOOST_DEFAULT_DURATION // 60},
]

SOFTBOOST_BINARY_SENSOR_ENTITIES = [
    {"key": "softboost_active", "icon": "mdi:fan-clock"},
]

SOFTBOOST_SWITCH_ENTITIES = [
    {"key": "softboost_fireplace_mode", "icon": "mdi:fire"},
]

SOFTBOOST_BUTTON_ENTITIES = [
    {"key": "softboost_start_stop"},
]
