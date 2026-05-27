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