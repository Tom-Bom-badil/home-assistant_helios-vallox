################################################################################
# Python script to control a central Helios Pro / Vallox SE ventilation device.
# Based on my old script - see https://github.com/Tom-Bom-badil/helios/wiki.
#
# Author: René Jahncke aka Tom-Bom-badil (https://github.com/Tom-Bom-badil)
#
# This script can
# - read all registers and output it on screen in text / dict / json format
# - read a specific register and output it in text, dic, json format
# - write to a named register in number format.
#
# For your convenience, you can permanently set a default IP and port of your
# LAN/Wifi-RS485 adaptor below in this script (see DEFAULT_IP and DEFAULT_PORT).
# Default action is --read_all, which outputs plain text line by line
#
# USAGE:
#
#   python3 ventcontrol.py [ip] [port] [action] [format]
#
# EXAMPLE CALLS:
#
# read all registers from the specified network settings:
#   python3 ventcontrol.py --ip 10.10.10.10 --port 1010 --read_all
#
# read all registers from default IP+Port (might take a few seconds):
#   python3 ventcontrol.py --read_all
#   python3 ventcontrol.py --read_all --json
#   python3 ventcontrol.py --read_all --dict
#
# read a single register only:
#   python3 ventcontrol.py --read_value fanspeed
#   python3 ventcontrol.py --read_value fanspeed --json
#   python3 ventcontrol.py --read_value fanspeed --dict
#
# write to a single register:
#   python3 ventcontrol.py --write_value fanspeed 5
################################################################################


import logging
import socket
import threading
import time
import array
import json
import argparse


# default network address and port of the LAN/Wifi RS485 adaptor
DEFAULT_IP = "192.168.178.38"
DEFAULT_PORT = 8234


# log settings
logging.basicConfig(
    filename='/config/custom_components/helios_vallox_ventilation/helios.log',  # file
    # level=logging.DEBUG,  # level
    level=logging.INFO,     # level
    format='%(asctime)s - %(levelname)s - %(message)s'  # format
)
logger = logging.getLogger("")


# threading settings - we need to prevent parallel execution of the script,
# as this can result in bus overload (it's still only 9.600 baud!)
execution_lock = threading.Lock()
operation_timeout = 50      # max execution time in seconds
def watchdog(stop_event):   # end script if max execution time is reached
    if not stop_event.wait(operation_timeout):
        logger.error("Watchdog: Timeout reached, stopping script.")
        raise TimeoutError(" Timeout reached, stopping script.")


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


# mapping bits to fan speeds
FANSPEEDS = {
    1: 1,
    3: 2,
    7: 3,
    15: 4,
    31: 5,
    63: 6,
    127: 7,
    255: 8
}


# mapping error messages / faults
COMPONENT_FAULTS = {
    5: 'Inlet air sensor fault',
    6: 'CO2 Alarm',
    7: 'Outside air sensor fault',
    8: 'Exhaust air sensor fault',
    9: 'Water coil frost warning',
    10: 'Outlet air sensor fault'
}


# mapping for registers and coils
REGISTERS_AND_COILS = {
    # Current fanspeed (EC300Pro: 1..8)
    "fanspeed"          : {"varid" : 0x29, 'type': 'fanspeed',     'bitposition': -1, 'read': True, 'write': True  },
    # Fanspeed after switching on
    "initial_fanspeed"  : {"varid" : 0xA9, 'type': 'fanspeed',     'bitposition': -1, 'read': True, 'write': True  },
    # Maximum settable fanspeed
    "max_fanspeed"      : {"varid" : 0xA5, 'type': 'fanspeed',     'bitposition': -1, 'read': True, 'write': True  },
    # NTC5K sensors: outside air temperature
    "outside_temp"      : {"varid" : 0x32, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },
    # NTC5K sensors: supply air temperature
    "inlet_temp"        : {"varid" : 0x35, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },
    # NTC5K sensors: extract / inside air temperature
    "outlet_temp"       : {"varid" : 0x34, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },
    # NTC5K sensors: exhaust air temperature
    "exhaust_temp"      : {"varid" : 0x33, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },
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
    "defrost_hysteresis": {"varid" : 0xB2, 'type': 'dec_special',  'bitposition': -1, 'read': True, 'write': True  },
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


# exception handler
class HeliosException(Exception):
    pass


# base class
class HeliosBase():

    def __init__(self, ip=DEFAULT_IP, port=DEFAULT_PORT):
        self._ip = ip
        self._port = port
        self._is_connected = False
        self._socket = None
        self._lock = threading.Lock()  # call threading
        self.GLOBAL_VALUES = {}        # value dict for this thread only

    def connect(self):
        if self._is_connected and self._socket:
            return True
        try:
            logger.debug("Helios: Connecting to socket...")
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((self._ip, self._port))
            self._is_connected = True
            return True
        except Exception as e:
            logger.error(f"Helios: Could not connect to {self._ip}:{self._port}. Error: {e}")
            return False

    def disconnect(self):
        if self._is_connected and self._socket:
            logger.debug("HeliosBase: Disconnecting socket...")
            self._socket.close()
            self._is_connected = False

    def _sendTelegram(self, telegram):
        if not self._is_connected:
            return False
        try:
            logger.debug(f"Sending telegram: {' '.join(f'{byte:02X}' for byte in telegram)}")
            self._socket.sendall(bytearray(telegram))
            return True
        except Exception as e:
            logger.error(f"Helios: Error sending telegram. {e}")
            return False

    def _readTelegram(self, sender, receiver, datapoint):
        try:
            timeout = time.time() + 5
            buffer = bytearray(6)
            while self._is_connected and timeout > time.time():
                data = self._socket.recv(6)
                if len(data) == 6:
                    buffer = data
                    if buffer[0] != 0x01:       # lots of noise on the RS485
                        logger.debug(f"Ignoring jitter data: {' '.join(f'{byte:02X}' for byte in buffer)}")
                        continue
                    if (buffer[0] == 0x01 and
                            buffer[1] == sender and
                            buffer[2] == receiver and
                            buffer[3] == datapoint):
                        logger.debug(f"Telegram received: {' '.join(f'{byte:02X}' for byte in buffer)}")
                        if datapoint == 0xB2:
                            return buffer[4] // 3
                        return buffer[4]
            return None
        except Exception as e:
            logger.error(f"Helios: Error reading telegram. {e}")
            return None

    def _createTelegram(self, sender, receiver, function, value):
        telegram = [1, sender, receiver, function, value, 0]
        telegram[5] = self._calculateCRC(telegram)
        return telegram

    def _calculateCRC(self, telegram):
        return sum(telegram[:-1]) % 256

    def _waitForBusQuiet(self):  # at least 1 character silence = 7ms

        logger.debug("Helios: Waiting for silence on bus...")
        got_slot = False
        backup_timeout = self._socket.gettimeout()    # save current timeout
        self._socket.settimeout(0.01)                 # watch the bus

        try:
            end = time.time() + 5  # wait for max 5 seconds, then stop
            last_activity = time.time()

            while end > time.time():
                try:
                    data = self._socket.recv(1)  # try to read a byte
                    if data: # yes, we have activity on the bus
                        last_activity = time.time()
                    else:    # no current activity; wait till 10ms reached
                        if time.time() - last_activity > 0.01:
                            got_slot = True
                            break
                except socket.timeout:  # timeout without data
                    if time.time() - last_activity > 0.01:  # 10 ms again
                        got_slot = True
                        break
        except Exception as e:
            logger.error(f"Helios: Error while waiting for bus silence: {e}")
        finally:
            self._socket.settimeout(backup_timeout)  # restore timeout

        if not got_slot:
            logger.warning("Helios: Bus silence not achieved within 3 seconds.")
        return got_slot

    def readValue(self, varname, retries=3):
        for attempt in range(retries):
            if not self._is_connected:
                logger.error("Helios: Not connected.")
                return None
            try:
                if not self._waitForBusQuiet():
                    logger.error("Helios: Bus not silent, cannot read value.")
                    continue

                var_id = REGISTERS_AND_COILS[varname]["varid"]
                telegram = self._createTelegram(BUS_ADDRESSES["_HA"], BUS_ADDRESSES["MB1"], 0, var_id)
                self._sendTelegram(telegram)

                if not self._waitForBusQuiet():
                    logger.error("Helios: Bus not silent before receiving data.")
                    continue

                value = self._readTelegram(BUS_ADDRESSES["MB1"], BUS_ADDRESSES["_HA"], var_id)
                if value is not None:
                    return value

            except Exception as e:
                logger.error(f"Helios: Error in readValue (Attempt {attempt + 1}): {e}")
            time.sleep(0.05)  # have a snickers before next attempt
        logger.error(f"Helios: Failed to read value for variable {varname} after {retries} retries.")
        return None


    def prepare_value_for_write(self, varname, value):

        if varname not in REGISTERS_AND_COILS:
            raise ValueError(f"Variable '{varname}' is not defined in REGISTERS_AND_COILS.")

        var_info = REGISTERS_AND_COILS[varname]
        
        if var_info["type"] == "temperature": # use index
            return NTC5K_TEMPERATURES.index(value)
            
        elif var_info["type"] == "fanspeed": # reverse mapping
            return {v: k for k, v in FANSPEEDS.items()}[value]

        elif var_info["type"] == "bit": # handle bit position
            current_value = self.readValue(varname)
            bit_pos = var_info["bitposition"]
            if value:
                return current_value | (1 << bit_pos)  # set
            else:
                return current_value & ~(1 << bit_pos)  # unset
            
        elif var_info["type"] == "dec": # a number
            return value

        elif var_info["type"] == "dec_special": # Register 0xB2: 0x03 = 1°C
            return value * 3


    def writeValue(self, varname, value):

        if not self._is_connected:
            logger.error("Helios: Not connected, cannot write register.")
            return False

        # valid var?
        if varname not in REGISTERS_AND_COILS:
            logger.error(f"Variable '{varname}' not defined.")
            return False

        # read-only var?
        var_info = REGISTERS_AND_COILS[varname]
        if not var_info.get("write", False):
            logger.error(f"Variable '{varname}' is read-only.")
            return False

        # safety function for 0x06 - !!!!DO NOT REMOVE OR RISK SEVERE DAMAGE!!!!
        if var_info['varid'] == 0x06:
            logger.critical("Helios: Trying to write register 0x06. Operation aborted to prevent system damage.")
            return False

        # prepare value
        formatted_value = self.prepare_value_for_write(varname, value)
        logger.debug(f"Attempting to write {value}/{formatted_value} to {varname}.")


        for target in ["FB*", "MB*", "MB1"]:
            
            # create telegram
            telegram = [
                0x01,
                BUS_ADDRESSES["_HA"],
                BUS_ADDRESSES[target],
                var_info["varid"],
                formatted_value,
                0
            ]
            telegram[5] = self._calculateCRC(telegram)

            # wait for silence
            if not self._waitForBusQuiet():
                logger.error("Helios: Bus not silent, cannot write value.")
                return False

            # send it
            if not self._sendTelegram(telegram):
                logger.error(f"Helios: Failed to write variable '{varname}'.")
                return False

            # confirm setting the variable to mainboard
            if target == "MB1":
                crc_telegram = [telegram[5]]
                self._sendTelegram(crc_telegram)
                logger.debug(f"Resent CRC to Mainboard to finalize writing.")

        logger.debug(f"Writing successful.")
        return True


    def resolve_variable(self, varid, data_byte):

        results = []  # returns unique variables only
        processed_bits = set()

        for var_name, details in REGISTERS_AND_COILS.items():

            if details["varid"] == varid:
                
                var_type = details["type"]
                if var_type == "bit":
                    bit_position = details["bitposition"]
                    if bit_position >= 0 and bit_position not in processed_bits:
                        value = 1 if (data_byte & (1 << bit_position)) else 0
                        results.append((var_name, value))
                        processed_bits.add(bit_position)
                elif var_type == "temperature":
                    if 0 <= data_byte < len(NTC5K_TEMPERATURES):
                        temperature = NTC5K_TEMPERATURES[data_byte]
                        results.append((var_name, temperature))
                elif var_type == "fanspeed":
                    fanspeed = FANSPEEDS.get(data_byte, "unknown")
                    results.append((var_name, fanspeed))
                elif var_type == "dec":
                    results.append((var_name, data_byte))
                elif var_type == "dec_special":
                    results.append((var_name, data_byte))

        return results


    def readAllValues(self, textoutput=True):

        logger.debug("Helios: Reading values of all registers and coils ...")

        varid_groups = {}  # prevent double handling of coil bytes
        for varname, details in REGISTERS_AND_COILS.items():
            varid = details["varid"]
            if varid not in varid_groups:
                varid_groups[varid] = []
            varid_groups[varid].append(varname)

        for varid, varnames in varid_groups.items():
            self._waitForBusQuiet()  # wait for silence
            time.sleep(0.02)         # 20 ms between requests
            value = self.readValue(varnames[0])  # request var1 only
            if value is not None:
                resolved_values = self.resolve_variable(varid, value)
                for resolved_value in resolved_values:
                    var_name, var_value = resolved_value
                    if var_value is not None:
                        self.GLOBAL_VALUES[var_name] = var_value
                        logger.debug(f"{var_name}: {var_value}")
                        if textoutput==True:
                            print(f"{var_name}: {var_value}")
                        if var_name == "fault_number":
                            error_text = COMPONENT_FAULTS.get(var_value, "none")
                            if textoutput==True:
                                print(f"fault_text: {error_text}")
                            self.GLOBAL_VALUES['fault_text'] = error_text
                    else:
                        logger.warning(f"Failed to resolve value for variable: {var_name}")
                        print(f"{var_name}: Failed to resolve value")
            else:
                logger.warning(f"Failed to read value for varid: {varid:02X}")
                for varname in varnames:
                    print(f"{varname}: Failed to read value")
                    
    def get_global_values(self):
            return self.GLOBAL_VALUES


def main():

    # argument parser
    parser = argparse.ArgumentParser(description="Helios / Vallox RS485 Control Script")
    parser.add_argument("--ip", metavar="IP", help="IP address of the RS485-Wifi/LAN adator (using default if not provided)", default=DEFAULT_IP)
    parser.add_argument("--port", type=int, metavar="PORT", help="Port of the RS485-Wifi/LAN adator (using default if not provided)", default=DEFAULT_PORT)
    parser.add_argument("--read_all", action="store_true", help="Read and output line-by-line all known variables.")
    parser.add_argument("--read_value", nargs=1, metavar="VARIABLE", help="Read and output a specific variable.")
    parser.add_argument("--dict", action="store_true", help="Like --read_all, but output as a DICT.")
    parser.add_argument("--json", action="store_true", help="Like --read_all, but output as a JSON.")
    parser.add_argument("--write_value", nargs=2, metavar=("VARIABLE", "VALUE"), help="Writes value into a variable.")

    args = parser.parse_args()

# ----------------------------------------
    # use IP and Port from arguments, if provided (otherwise use default)
    ip_address = args.ip
    port = args.port

    # initialize helios connection
    helios = HeliosBase(ip_address, port)
# ----------------------------------------

    # start watchdog thread
    stop_event = threading.Event()
    watchdog_thread = threading.Thread(target=watchdog, args=(stop_event,))
    watchdog_thread.start()

    try:
        logger.debug("~~ Starting - waiting for ok from threading")
        with execution_lock:
            logger.debug("Got ok from threading.")
            helios = HeliosBase()
            if helios.connect():
                logger.debug(f"Connected to Helios - {helios._ip}:{helios._port}")

                # read all variables
                if args.read_all or not (args.read_value or args.write_value):
                    # default output (no args): text
                    if not (args.dict or args.json):
                        helios.readAllValues()
                    # --dict
                    if args.dict:
                        helios.readAllValues(textoutput=False)
                        GLOBAL_VALUES = helios.get_global_values()
                        print(GLOBAL_VALUES)
                    # --json
                    if args.json:
                        helios.readAllValues(textoutput=False)
                        GLOBAL_VALUES = helios.get_global_values()
                        print(json.dumps(GLOBAL_VALUES, indent=4))

                # read a specific variable
                if args.read_value:
                    variable = args.read_value[0]
                    value = helios.readValue(variable)
                    if value is not None:
                        var_info = REGISTERS_AND_COILS.get(variable, {})
                        if var_info.get("type") == "temperature":
                            converted_value = NTC5K_TEMPERATURES[value]
                        elif var_info.get("type") == "fanspeed":
                            converted_value = FANSPEEDS.get(value, value)
                        elif var_info.get("type") == "bit":
                            bit_pos = var_info.get("bitposition", 0)
                            converted_value = bool(value & (1 << bit_pos))
                        elif var_info.get("type") == "dec_special":
                            converted_value = value // 3
                        else:
                            converted_value = value
                        if args.json:
                            output = {variable: converted_value}
                            print(json.dumps(output, indent=4))
                        elif args.dict:
                            output = {variable: converted_value}
                            print(output)
                        else:
                            print(f"{variable}: {converted_value}")

                    else:
                        logger.error(f"Failed to read value for {variable}.")

                # write a specific variable
                if args.write_value:
                    variable, raw_value = args.write_value
                    try:
                        value = int(raw_value)  # just to be on safe side
                        if helios.writeValue(variable, value):
                            print(f"Successfully wrote {value} to {variable}.")
                        else:
                            logger.error(f"Failed to write {value} to {variable}")
                    except ValueError:
                        logger.error(f"Invalid value provided for {variable}: {raw_value}")

                helios.disconnect()
                logger.debug("Disconnected from Helios.")

    except TimeoutError as te:
        print(f"Error: {te}")
    finally:
        stop_event.set()        # dear watchdog: we are done, thanks
        watchdog_thread.join()  # wait for end of watchdog thread


if __name__ == "__main__":
    main()
