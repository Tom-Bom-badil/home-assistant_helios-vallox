import array

# domain
DOMAIN = "helios_vallox_ventilation"

# default network address and port
DEFAULT_IP = "192.168.178.36"
DEFAULT_PORT = 502

# mapping for the four NTC5k temperature sensors
NTC5K_TEMPERATURES = array.array(
    "i",
    [
        -74,-70,-66,-62,-59,-56,-54,-52,-50,-48,-47,-46,-44,-43,-42,-41,-40,-39,-38,-37,-36,
        -35,-34,-33,-33,-32,-31,-30,-30,-29,-28,-28,-27,-27,-26,-25,-25,-24,-24,-23,-23,-22,
        -22,-21,-21,-20,-20,-19,-19,-19,-18,-18,-17,-17,-16,-16,-16,-15,-15,-14,-14,-14,-13,
        -13,-12,-12,-12,-11,-11,-11,-10,-10,-9,-9,-9,-8,-8,-8,-7,-7,-7,-6,-6,-6,-5,-5,-5,-4,
        -4,-4,-3,-3,-3,-2,-2,-2,-1,-1,-1,-1,0,0,0,1,1,1,2,2,2,3,3,3,4,4,4,5,5,5,5,6,6,6,7,7,
        7,8,8,8,9,9,9,10,10,10,11,11,11,12,12,12,13,13,13,14,14,14,15,15,15,16,16,16,17,17,
        18,18,18,19,19,19,20,20,21,21,21,22,22,22,23,23,24,24,24,25,25,26,26,27,27,27,28,28,
        29,29,30,30,31,31,32,32,33,33,34,34,35,35,36,36,37,37,38,38,39,40,40,41,41,42,43,43,
        44,45,45,46,47,48,48,49,50,51,52,53,53,54,55,56,57,59,60,61,62,63,65,66,68,69,71,73,
        75,77,79,81,82,86,90,93,97,100,100,100,100,100,100,100,100,100
    ]
)

# mapping for valid senders / receivers
BUS_ADDRESSES = {
    "MB*": 0x10,  # all mainboards
    "MB1": 0x11,  # mainboard 1
    "FB*": 0x20,  # alle remote controls
    "FB1": 0x21,  # remote control 1
    "LON": 0x28,  # LON bus module (if any)
    "_HA": 0x2E,  # this HA Python script; we are simulating a remote
    "_SH": 0x2F   # SmartHomeNG Python script; also simulating a remote
}

# mapping bits to fan speeds
FANSPEEDS = {
    1:   1,
    3:   2,
    7:   3,
    15:  4,
    31:  5,
    63:  6,
    127: 7,
    255: 8
}

# mapping error messages / faults
COMPONENT_FAULTS = {
    0:  '-',
    5:  'Supply air sensor fault',
    6:  'CO2 Alarm',
    7:  'Outdoor air sensor fault',
    8:  'Exhaust air sensor fault',
    9:  'Water coil frost warning',
    10: 'Extract air sensor fault'
}

# mapping for registers and coils
REGISTERS_AND_COILS = {
    # Current fanspeed (EC300Pro: 1..8)
    "fanspeed":                {"varid": 0x29, 'type': 'fanspeed',    'bitposition': -1, 'read': True, 'write': True },
    # Fanspeed after switching on
    "initial_fanspeed":        {"varid": 0xA9, 'type': 'fanspeed',    'bitposition': -1, 'read': True, 'write': True },
    # Maximum settable fanspeed
    "max_fanspeed":            {"varid": 0xA5, 'type': 'fanspeed',    'bitposition': -1, 'read': True, 'write': True },
    # NTC5K sensors: outside air temperature
    "temperature_outdoor_air": {"varid": 0x32, 'type': 'temperature', 'bitposition': -1, 'read': True, 'write': False},
    # NTC5K sensors: supply air temperature
    "temperature_supply_air":  {"varid": 0x35, 'type': 'temperature', 'bitposition': -1, 'read': True, 'write': False},
    # NTC5K sensors: return air temperature
    "temperature_extract_air": {"varid": 0x34, 'type': 'temperature', 'bitposition': -1, 'read': True, 'write': False},
    # NTC5K sensors: discharge air temperature
    "temperature_exhaust_air": {"varid": 0x33, 'type': 'temperature', 'bitposition': -1, 'read': True, 'write': False},
    # various coils in register 0xA3 that are displayed on the remote controls (0..3 read/write, 4..7 readonly)
    # FB LED1: on/off Caution: Remotes will not be switched back on automatically; initial_fanspeed set if done manually.
    "powerstate":              {"varid": 0xA3, 'type': 'bit',         'bitposition':  0, 'read': True, 'write': True },
    # FB LED2: CO2 warning
    "co2_indicator":           {"varid": 0xA3, 'type': 'bit',         'bitposition':  1, 'read': True, 'write': True },
    # FB LED3: Humidity warning
    "rh_indicator":            {"varid": 0xA3, 'type': 'bit',         'bitposition':  2, 'read': True, 'write': True },
    # FB LED4: 0 = summer mode with bypass, 1 = wintermode with heat regeneration (LED is on in winter mode)
    "winter_mode":             {"varid": 0xA3, 'type': 'bit',         'bitposition':  3, 'read': True, 'write': True },
    # FB icon 1: "Clean filter" warning
    "clean_filter":            {"varid": 0xA3, 'type': 'bit',         'bitposition':  4, 'read': True, 'write': False},
    # FB icon 2 2: Pre-/Post heating active
    "post_heating_on":         {"varid": 0xA3, 'type': 'bit',         'bitposition':  5, 'read': True, 'write': False},
    # FB icon 3: Error / fault
    "fault_detected":          {"varid": 0xA3, 'type': 'bit',         'bitposition':  6, 'read': True, 'write': False},
    # FB icon 4: Service request
    "service_requested":       {"varid": 0xA3, 'type': 'bit',         'bitposition':  7, 'read': True, 'write': False},
    # Summer mode: Activate bypass from this temperature onwards if fresh air °C (outside) < extract air °C (inside)
    "bypass_setpoint":         {"varid": 0xAF, 'type': 'temperature', 'bitposition': -1, 'read': True, 'write': True },
    # Activation temperature for pre / post heating
    "preheat_setpoint":        {"varid": 0xA7, 'type': 'temperature', 'bitposition': -1, 'read': True, 'write': True },
    # Pre / post heating is off (0) / on (1)
    "preheat_status":          {"varid": 0x70, 'type': 'bit',         'bitposition':  7, 'read': True, 'write': True },
    # Frost protection - switch off fresh air ventilator and heating below this temperature; -6 ... +15°C
    "defrost_setpoint":        {"varid": 0xA8, 'type': 'temperature', 'bitposition': -1, 'read': True, 'write': True },
    # Frost protection hysteresis - when to switch it on again (defrost_setpoint + (this_value/3)) --> 0x03 = 1°C
    "defrost_hysteresis":      {"varid": 0xB2, 'type': 'dec',         'bitposition': -1, 'read': True, 'write': True },
    # Boost mode: 0=fireplace  (ignition - no exhaust air in the first 15 minutes of boost); 1=normal boost mode
    "boost_mode":              {"varid": 0xAA, 'type': 'bit',         'bitposition':  5, 'read': True, 'write': True },
    # Switch boost on for 45 minutes (set to 1; will be reset by mainboard automatically)
    "activate_boost":          {"varid": 0x71, 'type': 'bit',         'bitposition':  5, 'read': True, 'write': True },
    # Current boost status (off/on)
    "boost_status":            {"varid": 0x71, 'type': 'bit',         'bitposition':  6, 'read': True, 'write': False},
    # Remaining minutes of boost if on
    "boost_remaining":         {"varid": 0x79, 'type': 'dec',         'bitposition': -1, 'read': True, 'write': False},
    # Fresh air vetilator off; set to 1 to switch off; requires to be set twice
    "input_fan_off":           {"varid": 0x08, 'type': 'bit',         'bitposition':  3, 'read': True, 'write': True },
    # Exhaust air vetilator off; set to 1 to switch off; requires to be set twice
    "output_fan_off":          {"varid": 0x08, 'type': 'bit',         'bitposition':  5, 'read': True, 'write': True },
    # rpm of fresh air ventilator (65...100% - pneumatic calibration; default=100)
    "input_fan_percent":       {"varid": 0xB0, 'type': 'dec',         'bitposition': -1, 'read': True, 'write': True },
    # rpm of exhaust air ventilator (65...100% - pneumatic calibration; default=100)
    "output_fan_percent":      {"varid": 0xB1, 'type': 'dec',         'bitposition': -1, 'read': True, 'write': True },   
    # Service reminder interval in months (used after reset f service reminder)
    "service_interval":        {"varid": 0xA6, 'type': 'dec',         'bitposition': -1, 'read': True, 'write': True },
    # Remaining months for current service reminder
    "service_due_months":      {"varid": 0xAB, 'type': 'dec',         'bitposition': -1, 'read': True, 'write': True },
    # Error / fault register. 0 = no fault. see COMPONENT_FAULTS above
    "fault_number":            {"varid": 0x36, 'type': 'dec',         'bitposition': -1, 'read': True, 'write': False},
    # Humidity reading sensor 1. 33H = 0% RH FFH = 100% RH
    "rh_sensor1_raw":          {"varid": 0x2F, 'type': 'dec',         'bitposition': -1, 'read': True, 'write': False},
    # Humidity reading sensor 2. 33H = 0% RH FFH = 100% RH
    "rh_sensor2_raw":          {"varid": 0x30, 'type': 'dec',         'bitposition': -1, 'read': True, 'write': False}
}
