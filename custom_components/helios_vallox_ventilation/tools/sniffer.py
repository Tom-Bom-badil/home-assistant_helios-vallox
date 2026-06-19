# Packet sniffer for Helios / Vallox ventilation devices
#
# How to use:
# At first, change the IP and port at the end of this file to the actual
# settings of your RS485 adaptor.
#
# Then run the file at a command line (press Ctrl-C when done):
# python3 sniffer.py

import logging
import socket
import array

SNIFFER_VERSION = "v2026.06.2"

# log settings
logging.basicConfig(
    filename="hex.log",          # file
    # level=logging.DEBUG,       # uncomment to set alternative log level
    level=logging.INFO,          # set log level
    format="%(asctime)s %(message)s",  # set log format
)
logger = logging.getLogger("")

# Mapping: Sender & receiver
SENDER_MAP = {
    0x11: "MB1",
    0x21: "FB1",
    0x2D: "HA1",
    0x2E: "HA2",
    0x2F: "SH_",
}

RECEIVER_MAP = {
    0x10: "MB*",
    0x11: "MB1",
    0x20: "FB*",
    0x21: "FB1",
    0x2D: "HA1",
    0x2E: "HA2",
    0x2F: "SH_",
}

# Known bitfield registers.
#
# IMPORTANT:
# Do not add / use register 0x06 here. It is explicitly unsafe and must not
# be touched. This sniffer may see it if another device sends it, but we do
# not actively decode or encourage its usage here.
BITFIELD_REGISTERS = {
    0x08: {
        "name": "indicator_flags",
        "bits": {
            1: "bypass_damper_summer",
            2: "fault_relay",
            3: "input_fan_off",
            4: "preheating_on",
            5: "output_fan_off",
            6: "fireplace_boost_switch",
        },
    },
    0x2D: {
        "name": "co2_sensor_presence_flags",
        "bits": {
            1: "co2_sensor1_present",
            2: "co2_sensor2_present",
            3: "co2_sensor3_present",
            4: "co2_sensor4_present",
            5: "co2_sensor5_present",
        },
    },
    0x6D: {
        "name": "status_1_flags",
        "bits": {
            0: "co2_fanspeed_up_request",
            1: "co2_fanspeed_down_request",
            2: "rh_fanspeed_down_request",
            3: "switch_fanspeed_down_request",
            6: "co2_alarm",
            7: "heat_recovery_cell_freezing_alarm",
        },
    },
    0x6F: {
        "name": "status_2_flags",
        "bits": {
            4: "water_radiator_freezing_alarm",
            7: "master_mode",
        },
    },
    0x70: {
        "name": "preheat_flags",
        "bits": {
            7: "preheating_off",
        },
    },
    0x71: {
        "name": "status_3_flags",
        "bits": {
            4: "remote_monitoring_active",
            5: "activate_boost",
            6: "boost_status",
        },
    },
    0xA3: {
        "name": "remote_control_indicators",
        "bits": {
            0: "powerstate",
            1: "co2_indicator",
            2: "rh_indicator",
            3: "winter_mode",
            4: "clean_filter",
            5: "post_heating_on",
            6: "fault_detected",
            7: "service_requested",
        },
    },
    0xAA: {
        "name": "program_flags",
        "bits": {
            4: "humidity_control_auto",
            5: "boost_mode",
            6: "water_radiator_model",
            7: "cascade_control",
        },
    },
    0xB5: {
        "name": "status_4_flags",
        "bits": {
            0: "max_speed_limit_always_active",
        },
    },
}

# Small cache only for nicer CO2 logging in the sniffer.
# The bus sends high and low byte as separate packets.
CO2_RAW_CACHE = {
    "co2_reading": {"upper": None, "lower": None},
    "co2_setting": {"upper": None, "lower": None},
}

# mapping for registers and coils
CONST_MAP_VARIABLES_TO_ID = {
    # Current fanspeed (EC300Pro: 1..8)
    "fanspeed": {
        "varid": 0x29,
        "type": "fanspeed",
        "bitposition": -1,
        "read": True,
        "write": True,
    },

    # Fanspeed after switching on
    "initial_fanspeed": {
        "varid": 0xA9,
        "type": "fanspeed",
        "bitposition": -1,
        "read": True,
        "write": True,
    },

    # Maximum settable fanspeed
    "max_fanspeed": {
        "varid": 0xA5,
        "type": "fanspeed",
        "bitposition": -1,
        "read": True,
        "write": True,
    },

    # Max currently measured humidity, raw value
    "rh_max_raw": {
        "varid": 0x2A,
        "type": "humidity_raw",
        "bitposition": -1,
        "read": True,
        "write": False,
    },

    # Max currently measured CO2 value, upper/lower byte
    "co2_reading_upper_byte": {
        "varid": 0x2B,
        "type": "co2_upper_raw",
        "pair": "co2_reading",
        "bitposition": -1,
        "read": True,
        "write": False,
    },
    "co2_reading_lower_byte": {
        "varid": 0x2C,
        "type": "co2_lower_raw",
        "pair": "co2_reading",
        "bitposition": -1,
        "read": True,
        "write": False,
    },

    # Installed CO2 sensors are decoded as bitfield 0x2D above.

    # Raw rH values from sensor 1 / 2
    "rh_sensor1_raw": {
        "varid": 0x2F,
        "type": "humidity_raw",
        "bitposition": -1,
        "read": True,
        "write": False,
    },
    "rh_sensor2_raw": {
        "varid": 0x30,
        "type": "humidity_raw",
        "bitposition": -1,
        "read": True,
        "write": False,
    },

    # NTC5K sensors: outside air temperature
    "temperature_outdoor_air": {
        "varid": 0x32,
        "type": "temperature",
        "bitposition": -1,
        "read": True,
        "write": False,
    },

    # NTC5K sensors: supply air temperature
    "temperature_supply_air": {
        "varid": 0x35,
        "type": "temperature",
        "bitposition": -1,
        "read": True,
        "write": False,
    },

    # NTC5K sensors: return air temperature
    "temperature_extract_air": {
        "varid": 0x34,
        "type": "temperature",
        "bitposition": -1,
        "read": True,
        "write": False,
    },

    # NTC5K sensors: discharge air temperature
    "temperature_exhaust_air": {
        "varid": 0x33,
        "type": "temperature",
        "bitposition": -1,
        "read": True,
        "write": False,
    },

    # Post-heating on counter. Percentage according to Vallox docs: X / 2.5.
    "post_heating_on_counter": {
        "varid": 0x55,
        "type": "post_heating_counter",
        "bitposition": -1,
        "read": True,
        "write": False,
    },

    # Various coils in register 0xA3 that are displayed on the remote controls
    # (0..3 read/write, 4..7 readonly). 0xA3 is decoded as bitfield above, but
    # the single mappings are kept for compatibility / lookup.
    #
    # FB LED1: on/off
    # Caution: Remotes will not be switched back on automatically;
    # initial_fanspeed set if done manually.
    "powerstate": {
        "varid": 0xA3,
        "type": "bit",
        "bitposition": 0,
        "read": True,
        "write": True,
    },

    # FB LED2: CO2 warning
    "co2_indicator": {
        "varid": 0xA3,
        "type": "bit",
        "bitposition": 1,
        "read": True,
        "write": False,
    },

    # FB LED3: Humidity warning
    "rh_indicator": {
        "varid": 0xA3,
        "type": "bit",
        "bitposition": 2,
        "read": True,
        "write": False,
    },

    # FB LED4: 0 = summer mode with bypass,
    # 1 = winter mode with heat regeneration (LED is on in winter mode)
    "winter_mode": {
        "varid": 0xA3,
        "type": "bit",
        "bitposition": 3,
        "read": True,
        "write": False,
    },

    # Kept as legacy alias for older notes/log wording.
    "summer_winter_mode": {
        "varid": 0xA3,
        "type": "bit",
        "bitposition": 3,
        "read": True,
        "write": False,
    },

    # FB icon 1: "Clean filter" warning
    "clean_filter": {
        "varid": 0xA3,
        "type": "bit",
        "bitposition": 4,
        "read": True,
        "write": False,
    },

    # FB icon 2: Pre-/Post heating active
    "post_heating_on": {
        "varid": 0xA3,
        "type": "bit",
        "bitposition": 5,
        "read": True,
        "write": False,
    },

    # FB icon 3: Error / fault
    "fault_detected": {
        "varid": 0xA3,
        "type": "bit",
        "bitposition": 6,
        "read": True,
        "write": False,
    },

    # FB icon 4: Service request
    "service_requested": {
        "varid": 0xA3,
        "type": "bit",
        "bitposition": 7,
        "read": True,
        "write": False,
    },

    # Summer mode: Activate bypass from this temperature onwards if
    # fresh air °C (outside) < extract air °C (inside)
    "bypass_setpoint": {
        "varid": 0xAF,
        "type": "temperature",
        "bitposition": -1,
        "read": True,
        "write": True,
    },

    # Activation temperature for pre / post heating
    "preheat_setpoint": {
        "varid": 0xA7,
        "type": "temperature",
        "bitposition": -1,
        "read": True,
        "write": True,
    },

    # Preheat status is decoded as bitfield 0x70 above, but the single mapping
    # is kept for compatibility / lookup.
    "preheat_status": {
        "varid": 0x70,
        "type": "bit",
        "bitposition": 7,
        "read": True,
        "write": True,
    },

    # Frost protection - switch off fresh air ventilator and heating below this
    # temperature; -6 ... +15°C
    "defrost_setpoint": {
        "varid": 0xA8,
        "type": "temperature",
        "bitposition": -1,
        "read": True,
        "write": True,
    },

    # Frost protection hysteresis - when to switch it on again
    # (defrost_setpoint + (this_value/3)) --> 0x03 = 1°C
    "defrost_hysteresis": {
        "varid": 0xB2,
        "type": "dec",
        "bitposition": -1,
        "read": True,
        "write": True,
    },

    # Boost mode: 0=fireplace (ignition - no exhaust air in the first
    # 15 minutes of boost); 1=normal boost mode
    "boost_mode": {
        "varid": 0xAA,
        "type": "bit",
        "bitposition": 5,
        "read": True,
        "write": True,
    },

    # Switch boost on for 45 minutes (set to 1; will be reset automatically)
    "activate_boost": {
        "varid": 0x71,
        "type": "bit",
        "bitposition": 5,
        "read": True,
        "write": True,
    },

    # Kept as legacy alias for older notes/log wording.
    "boost_on_switch": {
        "varid": 0x71,
        "type": "bit",
        "bitposition": 5,
        "read": True,
        "write": True,
    },

    # Current boost status (off/on)
    "boost_status": {
        "varid": 0x71,
        "type": "bit",
        "bitposition": 6,
        "read": True,
        "write": False,
    },

    # Remaining minutes of boost if on
    "boost_remaining": {
        "varid": 0x79,
        "type": "dec",
        "bitposition": -1,
        "read": True,
        "write": False,
    },

    # Fresh air ventilator off; set to 1 to switch off; requires to be set twice
    "input_fan_off": {
        "varid": 0x08,
        "type": "bit",
        "bitposition": 3,
        "read": True,
        "write": True,
    },

    # Exhaust air ventilator off; set to 1 to switch off; requires to be set twice
    "output_fan_off": {
        "varid": 0x08,
        "type": "bit",
        "bitposition": 5,
        "read": True,
        "write": True,
    },

    # RPM of fresh air ventilator (65...100% - pneumatic calibration; default=100)
    "input_fan_percent": {
        "varid": 0xB0,
        "type": "dec",
        "bitposition": -1,
        "read": True,
        "write": True,
    },

    # RPM of exhaust air ventilator (65...100% - pneumatic calibration; default=100)
    "output_fan_percent": {
        "varid": 0xB1,
        "type": "dec",
        "bitposition": -1,
        "read": True,
        "write": True,
    },

    # Service reminder interval in months (used after reset of service reminder)
    "service_interval": {
        "varid": 0xA6,
        "type": "dec",
        "bitposition": -1,
        "read": True,
        "write": True,
    },

    # Remaining months for current service reminder
    "service_due_months": {
        "varid": 0xAB,
        "type": "dec",
        "bitposition": -1,
        "read": True,
        "write": True,
    },

    # Basic humidity level / rH setpoint, raw value
    "basic_humidity_level_raw": {
        "varid": 0xAE,
        "type": "humidity_raw",
        "bitposition": -1,
        "read": True,
        "write": True,
    },

    # CO2 setting value, upper/lower byte
    "co2_setting_upper_byte": {
        "varid": 0xB3,
        "type": "co2_upper_raw",
        "pair": "co2_setting",
        "bitposition": -1,
        "read": True,
        "write": True,
    },
    "co2_setting_lower_byte": {
        "varid": 0xB4,
        "type": "co2_lower_raw",
        "pair": "co2_setting",
        "bitposition": -1,
        "read": True,
        "write": True,
    },

    # Error / fault register.
    # 0 = no fault.
    # see COMPONENT_FAULTS in the integration.
    "fault_number": {
        "varid": 0x36,
        "type": "dec",
        "bitposition": -1,
        "read": True,
        "write": False,
    },
}

CONST_TEMPERATURE = array.array(
    "i",
    [-74, -70, -66, -62, -59, -56, -54, -52, -50, -48, -47, -46, -44, -43, -42, -41, -40, -39, -38, -37, -36, -35, -34, -33, -33, -32, -31, -30, -30, -29, -28, -28, -27, -27, -26, -25, -25, -24, -24, -23, -23, -22, -22, -21, -21, -20, -20, -19, -19, -19, -18, -18, -17, -17, -16, -16, -16, -15, -15, -14, -14, -14, -13, -13, -12, -12, -12, -11, -11, -11, -10, -10, -9, -9, -9, -8, -8, -8, -7, -7, -7, -6, -6, -6, -5, -5, -5, -4, -4, -4, -3, -3, -3, -2, -2, -2, -1, -1, -1, -1, 0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8, 9, 9, 9, 10, 10, 10, 11, 11, 11, 12, 12, 12, 13, 13, 13, 14, 14, 14, 15, 15, 15, 16, 16, 16, 17, 17, 18, 18, 18, 19, 19, 19, 20, 20, 21, 21, 21, 22, 22, 22, 23, 23, 24, 24, 24, 25, 25, 26, 26, 27, 27, 27, 28, 28, 29, 29, 30, 30, 31, 31, 32, 32, 33, 33, 34, 34, 35, 35, 36, 36, 37, 37, 38, 38, 39, 40, 40, 41, 41, 42, 43, 43, 44, 45, 45, 46, 47, 48, 48, 49, 50, 51, 52, 53, 53, 54, 55, 56, 57, 59, 60, 61, 62, 63, 65, 66, 68, 69, 71, 73, 75, 77, 79, 81, 82, 86, 90, 93, 97, 100, 100, 100, 100, 100, 100, 100, 100, 100],
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


def calculate_checksum(packet_without_checksum):
    return sum(packet_without_checksum) & 0xFF


def format_bytes(data):
    return " ".join(f"{byte:02x}" for byte in data)


def log_line(text):
    print(text)
    logger.info(text)


def resolve_bitfield(varid, data_byte):
    bitfield = BITFIELD_REGISTERS.get(varid)
    if bitfield is None:
        return None

    name = bitfield["name"]
    bits = bitfield["bits"]

    bit_values = ", ".join(
        f"{flag_name}={1 if data_byte & (1 << bit_position) else 0}"
        for bit_position, flag_name in bits.items()
    )

    return f"{name}={data_byte:08b} [{bit_values}]"


def format_humidity_raw(var_name, data_byte):
    humidity = (data_byte - 51) / 2.04
    return f"{var_name}=0x{data_byte:02x} ({data_byte}) -> {humidity:.1f}% RH"


def format_co2_raw(var_name, details, data_byte):
    pair = details.get("pair")
    var_type = details["type"]

    if pair not in CO2_RAW_CACHE:
        return f"{var_name}=0x{data_byte:02x} ({data_byte})"

    if var_type == "co2_upper_raw":
        CO2_RAW_CACHE[pair]["upper"] = data_byte
    elif var_type == "co2_lower_raw":
        CO2_RAW_CACHE[pair]["lower"] = data_byte

    upper = CO2_RAW_CACHE[pair]["upper"]
    lower = CO2_RAW_CACHE[pair]["lower"]

    if upper is None or lower is None:
        return f"{var_name}=0x{data_byte:02x} ({data_byte})"

    co2_value = upper * 256 + lower
    return f"{var_name}=0x{data_byte:02x} ({data_byte}) -> {pair}={co2_value} ppm"


def format_post_heating_counter(var_name, data_byte):
    percent = data_byte / 2.5
    return f"{var_name}=0x{data_byte:02x} ({data_byte}) -> {percent:.1f}%"


def resolve_variable(varid, data_byte):
    # Decode known bitfield registers as whole bytes first. This avoids
    # misleading logs like "powerstate" for the complete 0xA3 byte.
    bitfield_text = resolve_bitfield(varid, data_byte)
    if bitfield_text is not None:
        return bitfield_text

    # get variables based on ID
    for var_name, details in CONST_MAP_VARIABLES_TO_ID.items():
        if details["varid"] == varid:
            var_type = details["type"]

            if var_type == "bit":
                bit_position = details["bitposition"]
                value = "1" if (data_byte & (1 << bit_position)) else "0"
                return f"{var_name} (Bit {bit_position}): {value}"

            if var_type == "temperature":
                temperature_index = data_byte
                if 0 <= temperature_index < len(CONST_TEMPERATURE):
                    temperature = CONST_TEMPERATURE[temperature_index]
                    return f"{var_name}: {temperature}°C"
                return f"{var_name}: invalid temperature raw=0x{data_byte:02x}"

            if var_type == "fanspeed":
                fanspeed = CONST_FANSPEED.get(data_byte, "unknown")
                return f"{var_name}: {fanspeed}"

            if var_type == "dec":
                return f"{var_name}: {data_byte}"

            if var_type == "humidity_raw":
                return format_humidity_raw(var_name, data_byte)

            if var_type in {"co2_upper_raw", "co2_lower_raw"}:
                return format_co2_raw(var_name, details, data_byte)

            if var_type == "post_heating_counter":
                return format_post_heating_counter(var_name, data_byte)

            return f"{var_name}"

    return f"unknown variable 0x{varid:02x}"


def find_variable_name(varid):
    # Return bitfield name first, so requests are logged as
    # "querying remote_control_indicators" instead of "querying powerstate".
    bitfield = BITFIELD_REGISTERS.get(varid)
    if bitfield is not None:
        return bitfield["name"]

    # return variable name or 'Unbekannt / unknown'
    for var_name, details in CONST_MAP_VARIABLES_TO_ID.items():
        if details["varid"] == varid:
            return var_name

    return f"Unknown variable 0x{varid:02x}"


def decode_valid_packet(packet):
    sender = packet[1]
    receiver = packet[2]
    variable_id = packet[3]
    data_byte = packet[4]

    sender_text = SENDER_MAP.get(sender, "???")
    receiver_text = RECEIVER_MAP.get(receiver, "???")
    sender_receiver = f"{sender_text}>{receiver_text}".ljust(10)
    formatted_line = format_bytes(packet)

    if variable_id == 0x00:
        # It is a read request (byte 5 = variable).
        variable_name = find_variable_name(data_byte)
        return f"{formatted_line.ljust(20)} {sender_receiver}querying {variable_name}"

    # It is data.
    variable_text = resolve_variable(variable_id, data_byte)
    return f"{formatted_line.ljust(20)} {sender_receiver}{variable_text}"


def connect_and_receive(ip, port):
    # make connection to device and start receiving data
    client_socket = None

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, port))
        buffer = b""

        log_line(f"sniffer_version={SNIFFER_VERSION}")

        while True:
            data = client_socket.recv(1024)
            if not data:
                break

            buffer += data

            while len(buffer) >= 6:
                # standard telegram: 6 Bytes, always starting with 0x01
                if buffer[0] != 0x01:
                    # Log invalid data up to the next possible telegram start.
                    jitter_end = buffer.find(b"\x01")
                    if jitter_end == -1:
                        jitter_end = len(buffer)

                    jitter = buffer[:jitter_end]
                    buffer = buffer[jitter_end:]

                    if jitter:
                        jitter_hex = format_bytes(jitter)
                        log_line(f"{jitter_hex.ljust(20)} jitter")
                    continue

                packet = buffer[:6]
                expected_checksum = calculate_checksum(packet[:5])
                actual_checksum = packet[5]

                if actual_checksum != expected_checksum:
                    # Do not decode broken packets. Keep them visible and resync
                    # by removing only the leading 0x01. This preserves possible
                    # valid telegrams starting later inside the buffered data.
                    packet_hex = format_bytes(packet)
                    log_line(
                        f"{packet_hex.ljust(20)} checksum mismatch "
                        f"(expected 0x{expected_checksum:02x}, got 0x{actual_checksum:02x})"
                    )
                    buffer = buffer[1:]
                    continue

                log_line(decode_valid_packet(packet))
                buffer = buffer[6:]

                # End-to-end acknowledged service: after a unicast write, the
                # receiver may acknowledge by sending the checksum byte only.
                # Keep this visible, but do not let it become generic jitter.
                if (
                    packet[3] != 0x00
                    and packet[2] not in (0x10, 0x20)
                    and len(buffer) >= 1
                    and buffer[0] == actual_checksum
                ):
                    log_line(f"{actual_checksum:02x}                  ack checksum")
                    buffer = buffer[1:]

    except KeyboardInterrupt:
        print("Stopped.")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if client_socket is not None:
            client_socket.close()


if __name__ == "__main__":
    server_ip = "192.168.178.36"
    server_port = 502

    connect_and_receive(server_ip, server_port)
