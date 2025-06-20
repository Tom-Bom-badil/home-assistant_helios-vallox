# Packet sniffer for Helios / Vallox ventilation devices
# How to use:
# At first, change the IP and port at the end of this file to the actual settings of your RS485 adaptor.
# Then run the file at a command line (press Ctrl-C when done):
#    python3 sniffer.py

import logging
import socket
import array


# log settings
logging.basicConfig(
    filename='hex.log',  # file
    # level=logging.DEBUG,  # uncomment to set alternative log level
    level=logging.INFO,     # set log level
    format='%(asctime)s       %(message)s'  # set log format
)
logger = logging.getLogger("")


# Mapping: Sender & receiver
SENDER_MAP = {
    0x11: "MB1",
    0x21: "FB1",
    0x2D: "HA1",
    0x2E: "HA2",
    0x2F: "SH_"
}

RECEIVER_MAP = {
    0x10: "MB*",
    0x11: "MB1",
    0x20: "FB*",
    0x21: "FB1",
    0x2D: "HA1",
    0x2E: "HA2",
    0x2F: "SH_"
}

# mapping for registers and coils
CONST_MAP_VARIABLES_TO_ID = {
    # Current fanspeed (EC300Pro: 1..8)
    "fanspeed"          : {"varid" : 0x29, 'type': 'fanspeed',     'bitposition': -1, 'read': True, 'write': True  },
    # Fanspeed after switching on
    "initial_fanspeed"  : {"varid" : 0xA9, 'type': 'fanspeed',     'bitposition': -1, 'read': True, 'write': True  },
    # Maximum settable fanspeed
    "max_fanspeed"      : {"varid" : 0xA5, 'type': 'fanspeed',     'bitposition': -1, 'read': True, 'write': True  },
    # NTC5K sensors: outside air temperature
    "temperature_outdoor_air"      : {"varid" : 0x32, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },
    # NTC5K sensors: supply air temperature
    "temperature_supply_air"        : {"varid" : 0x35, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },
    # NTC5K sensors: return air temperature
    "temperature_extract_air"       : {"varid" : 0x34, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },
    # NTC5K sensors: discharge air temperature
    "temperature_exhaust_air"      : {"varid" : 0x33, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },
    # various coils in register 0xA3 that are displayed on the remote controls (0..3 read/write, 4..7 readonly)
    # FB LED1: on/off Caution: Remotes will not be switched back on automatically; initial_fanspeed set if done manually.
    "powerstate"        : {"varid" : 0xA3, 'type': 'bit',          'bitposition':  0, 'read': True, 'write': True  },
    # FB LED2: CO2 warning
    "co2_indicator"     : {"varid" : 0xA3, 'type': 'bit',          'bitposition':  1, 'read': True, 'write': False },
    # FB LED3: Humidity warning
    "rh_indicator"      : {"varid" : 0xA3, 'type': 'bit',          'bitposition':  2, 'read': True, 'write': False },
    # FB LED4: 0 = summer mode with bypass, 1 = wintermode with heat regeneration (LED is on in winter mode)
    "summer_winter_mode": {"varid" : 0xA3, 'type': 'bit',          'bitposition':  3, 'read': True, 'write': False },
    # FB icon 1: "Clean filter" warning
    "clean_filter"      : {"varid" : 0xA3, 'type': 'bit',          'bitposition':  4, 'read': True, 'write': False },
    # FB icon 2 2: Pre-/Post heating active
    "post_heating_on"   : {"varid" : 0xA3, 'type': 'bit',          'bitposition':  5, 'read': True, 'write': False },
    # FB icon 3: Error / fault
    "fault_detected"    : {"varid" : 0xA3, 'type': 'bit',          'bitposition':  6, 'read': True, 'write': False },
    # FB icon 4: Service request
    "service_requested" : {"varid" : 0xA3, 'type': 'bit',          'bitposition':  7, 'read': True, 'write': False },
    # Summer mode: Activate bypass from this temperature onwards if fresh air °C (outside) < extract air °C (inside)
    "bypass_setpoint"   : {"varid" : 0xAF, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': True  },
    # Activation temperature for pre / post heating
    "preheat_setpoint"  : {"varid" : 0xA7, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': True  },
    # Pre / post heating is off (0) / on (1)
    "preheat_status"    : {"varid" : 0x70, 'type': 'bit',          'bitposition':  7, 'read': True, 'write': True  },
    # Frost protection - switch off fresh air ventilator and heating below this temperature; -6 ... +15°C
    "defrost_setpoint"  : {"varid" : 0xA8, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': True  },
    # Frost protection hysteresis - when to switch it on again (defrost_setpoint + (this_value/3)) --> 0x03 = 1°C
#    "defrost_hysteresis": {"varid" : 0xB2, 'type': 'dec_special',  'bitposition': -1, 'read': True, 'write': True  },
    "defrost_hysteresis": {"varid" : 0xB2, 'type': 'dec',  'bitposition': -1, 'read': True, 'write': True  },
    # Boost mode: 0=fireplace  (ignition - no exhaust air in the first 15 minutes of boost); 1=normal boost mode
    "boost_mode"        : {"varid" : 0xAA, 'type': 'bit',          'bitposition':  5, 'read': True, 'write': True  },
    # Switch boost on for 45 minutes (set to 1; will be reset automatically)
    "boost_on_switch"   : {"varid" : 0x71, 'type': 'bit',          'bitposition':  5, 'read': True, 'write': True  },
    # Current boost status (off/on)
    "boost_status"      : {"varid" : 0x71, 'type': 'bit',          'bitposition':  6, 'read': True, 'write': False },
    # Remaining minutes of boost if on
    "boost_remaining"   : {"varid" : 0x79, 'type': 'dec',          'bitposition': -1, 'read': True, 'write': False },
    # Fresh air vetilator off; set to 1 to switch off; requires to be set twice
    "input_fan_off"     : {"varid" : 0x08, 'type': 'bit',          'bitposition':  3, 'read': True, 'write': True  },
    # Exhaust air vetilator off; set to 1 to switch off; requires to be set twice
    "output_fan_off"    : {"varid" : 0x08, 'type': 'bit',          'bitposition':  5, 'read': True, 'write': True  },
	# rpm of fresh air ventilator (65...100% - pneumatic calibration; default=100)
    "input_fan_percent" : {"varid" : 0xB0, 'type': 'dec',          'bitposition': -1, 'read': True, 'write': True  },
	# rpm of exhaust air ventilator (65...100% - pneumatic calibration; default=100)
    "output_fan_percent": {"varid" : 0xB1, 'type': 'dec',          'bitposition': -1, 'read': True, 'write': True  },   
    # Service reminder interval in months (used after reset f service reminder)
    "service_interval"  : {"varid" : 0xA6, 'type': 'dec',          'bitposition': -1, 'read': True, 'write': True  },
    # Remaining months for current service reminder
    "service_due_months": {"varid" : 0xAB, 'type': 'dec',          'bitposition': -1, 'read': True, 'write': True  },
    # Error / fault register. 0 = no fault. see COMPONENT_FAULTS below
    "fault_number"      : {"varid" : 0x36, 'type': 'dec',          'bitposition': -1, 'read': True, 'write': False }
}

CONST_TEMPERATURE = array.array(
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

# Mapping: fanspeed
CONST_FANSPEED = {
    1: 1,
    3: 2,
    7: 3,
    15: 4,
    31: 5,
    63: 6,
    127: 7,
    255: 8,
}

def adjust_abbreviations(text):
    # replace long names with abbreviations
    return (
        text.replace("Mainboard_1", "MB1")
        .replace("Remote_1", "FB1")
        .replace("Alle_Remotes", "FB*")
        .replace("Remote_Software", "_SH")
        .replace("-->", ">")
    )

def resolve_variable(varid, data_byte):
    # get variables based on ID
    for var_name, details in CONST_MAP_VARIABLES_TO_ID.items():
        if details["varid"] == varid:
            var_type = details["type"]
            if var_type == "bit":
                bit_position = details["bitposition"]
                value = "1" if (data_byte & (1 << bit_position)) else "0"
                return f"{var_name} (Bit {bit_position}): {value}"
            elif var_type == "temperature":
                temperature_index = data_byte
                if 0 <= temperature_index < len(CONST_TEMPERATURE):
                    temperature = CONST_TEMPERATURE[temperature_index]
                    return f"{var_name}: {temperature}°C"
            elif var_type == "fanspeed":
                fanspeed = CONST_FANSPEED.get(data_byte, "Unbekannt")
                return f"{var_name}: {fanspeed}"
            elif var_type == "dec":
                return f"{var_name}: {data_byte}"
            return f"{var_name}"
    return f"unknown variable 0x{varid:02x}"

def find_variable_name(varid):
    # return variable name or 'Unbekannt / unknown'
    for var_name, details in CONST_MAP_VARIABLES_TO_ID.items():
        if details["varid"] == varid:
            return var_name
    return f"Unknown variable 0x{varid:02x}"

def connect_and_receive(ip, port):
    # make connection to device and start reveiving data
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, port))
        buffer = b""
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            buffer += data

            while len(buffer) >= 6:  # standard telegram: 6 Bytes
                if buffer[0] != 0x01:
                    # remove invalid data (jitter)
                    jitter_end = buffer.find(b'\x01')  # find next 0x01 = telegram start
                    if jitter_end == -1:
                        jitter_end = len(buffer)
                    jitter = buffer[:jitter_end]
                    buffer = buffer[jitter_end:]
                    jitter_hex = " ".join(f"{byte:02x}" for byte in jitter)
                    print(f"{jitter_hex.ljust(20)} jitter")
                    logger.info(f"{jitter_hex.ljust(20)} jitter")
                    continue

                sender = buffer[1]
                receiver = buffer[2]
                variable_id = buffer[3]
                data_byte = buffer[4]
                        
                try:
                    sender_text = SENDER_MAP[sender]
                except:
                    sender_text = '???'

                try:
                    receiver_text = RECEIVER_MAP[receiver]
                except:
                    receiver_text = '???'

                sender_receiver = f"{sender_text}>{receiver_text}".ljust(10)

                if variable_id == 0x00:
                    # its a read request (byte 5 = variable)
                    variable_name = find_variable_name(data_byte)
                    formatted_line = " ".join(f"{byte:02x}" for byte in buffer[:6])
                    print(f"{formatted_line.ljust(20)} {sender_receiver}request {variable_name}")
                    logger.info(f"{formatted_line.ljust(20)} {sender_receiver}request {variable_name}")
                else:
                    # its data
                    variable_text = resolve_variable(variable_id, data_byte).replace(",", "")
                    formatted_line = " ".join(f"{byte:02x}" for byte in buffer[:6])
                    print(f"{formatted_line.ljust(20)} {sender_receiver}{variable_text}")
                    logger.info(f"{formatted_line.ljust(20)} {sender_receiver}{variable_text}")

                buffer = buffer[6:]
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    server_ip = "192.168.178.36"
    server_port = 502
    connect_and_receive(server_ip, server_port)
