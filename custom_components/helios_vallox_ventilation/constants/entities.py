# Entity definitions (replaces vent_conf.yaml)

SENSOR_ENTITIES = [
    {"key": "temperature_outdoor_air", "unit": "°C", "device_class": "temperature", "state_class": "measurement", "icon": "mdi:thermometer"},
    {"key": "temperature_supply_air", "unit": "°C", "device_class": "temperature", "state_class": "measurement", "icon": "mdi:thermometer"},
    {"key": "temperature_extract_air", "unit": "°C", "device_class": "temperature", "state_class": "measurement", "icon": "mdi:thermometer"},
    {"key": "temperature_exhaust_air", "unit": "°C", "device_class": "temperature", "state_class": "measurement", "icon": "mdi:thermometer"},
    {"key": "boost_remaining", "unit": "min", "device_class": "duration", "state_class": "measurement", "icon": "mdi:fan-clock"},
    {"key": "fault_number", "unit": None, "device_class": None, "state_class": "measurement", "icon": "mdi:alert"},
    {"key": "fault_text", "unit": None, "device_class": None, "state_class": None, "icon": "mdi:alert"},
    {"key": "rh_sensor1_raw", "unit": None, "device_class": None, "state_class": None, "icon": "mdi:water-percent"},
    {"key": "rh_sensor2_raw", "unit": None, "device_class": None, "state_class": None, "icon": "mdi:water-percent"},
    {"key": "co2_reading_upper_byte", "unit": None, "device_class": None, "state_class": None, "icon": "mdi:molecule-co2"},
    {"key": "co2_reading_lower_byte", "unit": None, "device_class": None, "state_class": None, "icon": "mdi:molecule-co2"},
    {"key": "co2_setting_upper_byte", "unit": None, "device_class": None, "state_class": None, "icon": "mdi:molecule-co2"},
    {"key": "co2_setting_lower_byte", "unit": None, "device_class": None, "state_class": None, "icon": "mdi:molecule-co2"},
    {"key": "temperature_reduction", "unit": "°C", "device_class": "temperature", "state_class": "measurement", "icon": "mdi:thermometer", "description": "Heat recovery - temperature reduction of outgoing air"},
    {"key": "temperature_gain", "unit": "°C", "device_class": "temperature", "state_class": "measurement", "icon": "mdi:thermometer", "description": "Heat recovery - temperature gain of incoming air"},
    {"key": "temperature_balance", "unit": "°C", "device_class": "temperature", "state_class": "measurement", "icon": "mdi:thermometer", "description": "Difference temperature gain - temperature reduction"},
    {"key": "efficiency", "unit": "%", "device_class": None, "state_class": "measurement", "icon": "mdi:percent"},
    {"key": "rh_sensor1", "unit": "%", "device_class": "humidity", "state_class": "measurement", "icon": "mdi:water-percent", "description": "Relative humidity sensor 1"},
    {"key": "rh_sensor2", "unit": "%", "device_class": "humidity", "state_class": "measurement", "icon": "mdi:water-percent", "description": "Relative humidity sensor 2"},
    {"key": "co2_concentration", "unit": "ppm", "device_class": "carbon_dioxide", "state_class": "measurement", "icon": "mdi:molecule-co2", "description": "CO2 concentration"},
    {"key": "co2_setting_value", "unit": "ppm", "device_class": "carbon_dioxide", "state_class": None, "icon": "mdi:molecule-co2", "description": "CO2 control setpoint"},
    {"key": "din_airflow_moisture", "unit": "m³/h", "device_class": None, "state_class": None, "icon": "mdi:fan", "description": "DIN airflow for moisture protection"},
    {"key": "din_airflow_reduced", "unit": "m³/h", "device_class": None, "state_class": None, "icon": "mdi:fan", "description": "DIN airflow for reduced exchange"},
    {"key": "din_airflow_normal", "unit": "m³/h", "device_class": None, "state_class": None, "icon": "mdi:fan", "description": "DIN airflow for normal exchange"},
    {"key": "din_airflow_boost", "unit": "m³/h", "device_class": None, "state_class": None, "icon": "mdi:fan", "description": "DIN airflow for boost exchange"},
    {"key": "effective_airflow", "unit": "m³/h", "device_class": None, "state_class": "measurement", "icon": "mdi:fan", "description": "Current effective airflow"},
    {"key": "electrical_power", "unit": "W", "device_class": "power", "state_class": "measurement", "icon": "mdi:flash", "description": "Current electrical power consumption"},
]

BINARY_SENSOR_ENTITIES = [
    {"key": "boost_status", "device_class": None, "icon": "mdi:tooltip-question"},
    {"key": "fault_detected", "device_class": "problem", "icon": "mdi:alert"},
    {"key": "clean_filter", "device_class": "problem", "icon": "mdi:alert"},
    {"key": "service_requested", "device_class": "problem", "icon": "mdi:alert"},
    {"key": "post_heating_on", "device_class": "heat", "icon": "mdi:heating-coil"},
    {"key": "co2_sensor1_present", "device_class": "connectivity", "icon": "mdi:molecule-co2"},
    {"key": "co2_sensor2_present", "device_class": "connectivity", "icon": "mdi:molecule-co2"},
    {"key": "co2_sensor3_present", "device_class": "connectivity", "icon": "mdi:molecule-co2"},
    {"key": "co2_sensor4_present", "device_class": "connectivity", "icon": "mdi:molecule-co2"},
    {"key": "co2_sensor5_present", "device_class": "connectivity", "icon": "mdi:molecule-co2"},
    {"key": "co2_alarm", "device_class": "problem", "icon": "mdi:alert"},
]

NUMBER_ENTITIES = [
    {"key": "fanspeed", "unit": None, "min": 1, "max": 8, "step": 1, "mode": "slider", "icon": "mdi:speedometer-medium", "description": "Fan speed", "factory_setting": None},
    {"key": "initial_fanspeed", "unit": "level", "min": 1, "max": 8, "step": 1, "mode": "slider", "icon": "mdi:speedometer-slow", "description": "Initial fan speed after switching on", "factory_setting": 1},
    {"key": "max_fanspeed", "unit": "level", "min": 1, "max": 8, "step": 1, "mode": "slider", "icon": "mdi:speedometer", "description": "Maximum fan speed available to remotes", "factory_setting": 8},
    {"key": "bypass_setpoint", "unit": "°C", "min": 0, "max": 25, "step": 1, "mode": "box", "icon": "mdi:thermometer", "description": None, "factory_setting": 10},
    {"key": "preheat_setpoint", "unit": "°C", "min": -10, "max": 10, "step": 1, "mode": "box", "icon": "mdi:thermometer", "description": None, "factory_setting": -3},
    {"key": "defrost_setpoint", "unit": "°C", "min": -6, "max": 15, "step": 1, "mode": "box", "icon": "mdi:thermometer", "description": None, "factory_setting": 3},
    {"key": "defrost_hysteresis", "unit": "°C", "min": 1, "max": 10, "step": 1, "mode": "box", "icon": "mdi:thermometer", "description": None, "factory_setting": 3},
    {"key": "input_fan_percent", "unit": "%", "min": 65, "max": 100, "step": 1, "mode": "slider", "icon": "mdi:percent", "description": None, "factory_setting": 100},
    {"key": "output_fan_percent", "unit": "%", "min": 65, "max": 100, "step": 1, "mode": "slider", "icon": "mdi:percent", "description": None, "factory_setting": 100},
    {"key": "service_interval", "unit": "months", "min": 1, "max": 12, "step": 1, "mode": "box", "icon": "mdi:calendar-multiple", "description": None, "factory_setting": 4},
    {"key": "service_due_months", "unit": "months", "min": 0, "max": 12, "step": 1, "mode": "box", "icon": "mdi:calendar-end", "description": None, "factory_setting": None},
]

SWITCH_ENTITIES = [
    {"key": "powerstate", "icon": "mdi:power-settings"},
    {"key": "co2_indicator", "icon": "mdi:alert"},
    {"key": "rh_indicator", "icon": "mdi:alert"},
    {"key": "preheat_status", "icon": "mdi:tooltip-question"},
    {"key": "activate_boost", "icon": "mdi:fan"},
    {"key": "input_fan_off", "icon": "mdi:fan-off"},
    {"key": "output_fan_off", "icon": "mdi:fan-off"},
]

SELECT_ENTITIES = [
    {"key": "boost_mode", "icon": "mdi:fan-speed-2", "options": {0: "Fireplace", 1: "Normal"}},
    {"key": "winter_mode", "icon": "mdi:snowflake-thermometer", "options": {0: "Summer", 1: "Winter"}},
]
