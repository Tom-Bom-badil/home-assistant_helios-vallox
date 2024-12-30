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
# LAN/Wifi-RS485 adaptor in const.py (see DEFAULT_IP and DEFAULT_PORT).
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
from const import NTC5K_TEMPERATURES, DEFAULT_IP, DEFAULT_PORT, BUS_ADDRESSES
from const import FANSPEEDS, COMPONENT_FAULTS, REGISTERS_AND_COILS


# log settings
logging.basicConfig(
    filename='/config/custom_components/helios_vallox_ventilation/helios.log',  # file
    # level=logging.DEBUG,  # level
    level=logging.INFO,     # level
    format='%(asctime)s - %(levelname)s - %(message)s'  # format
)
logger = logging.getLogger("")


# threading settings - we need to prevent parallel execution of the script,
# as this can result in bus overload (it's still 9.600 baud only!)
execution_lock = threading.Lock()
operation_timeout = 50      # max execution time in seconds
def watchdog(stop_event):   # end script if max execution time is reached
    if not stop_event.wait(operation_timeout):
        logger.error("Watchdog: Timeout reached, stopping script.")
        raise TimeoutError(" Timeout reached, stopping script.")


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
                    if buffer[0] != 0x01:       # sometimes lots of noise on the RS485
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


    def calculate_derived_values(self, measured_values):

        try:

            # get temperatures
            temp_outside = measured_values.get("temperature_outdoor_air")
            temp_inlet = measured_values.get("temperature_supply_air")
            temp_outlet = measured_values.get("temperature_extract_air")
            temp_exhaust = measured_values.get("temperature_exhaust_air")

            # calculate reduction / gain / (dis-)balance
            temperature_reduction = (
                temp_outlet - temp_exhaust
                if temp_outlet is not None and temp_exhaust is not None
                else None
            )
            temperature_gain = (
                temp_inlet - temp_outside
                if temp_inlet is not None and temp_outside is not None
                else None
            )
            temperature_balance = (
                temperature_reduction - temperature_gain
                if temperature_reduction is not None and temperature_gain is not None
                else None
            )

            # calculate efficientcy
            efficiency = None
            if (
                temp_inlet is not None
                and temp_outside is not None
                and temp_outlet is not None
            ):
                delta_outside = temp_outlet - temp_outside
                if delta_outside == 0:
                    # temp_extract == temp_outdoor would lead to div/0
                    efficiency = 0
                elif delta_outside > 0:
                    efficiency = (temperature_gain / delta_outside) * 100
                else:
                    efficiency = 0
                # limit to 0..100%
                if efficiency is not None:
                    efficiency = int(max(0, min(efficiency, 100)))

            return {
                "temperature_reduction": temperature_reduction,
                "temperature_gain": temperature_gain,
                "temperature_balance": temperature_balance,
                "efficiency": efficiency,
            }

        except Exception as e:
            logger.error(f"Error in temperature/efficiency calculations: {e}")
            return {
                "temperature_reduction": None,
                "temperature_gain": None,
                "temperature_balance": None,
                "efficiency": None,
            }


    def readAllValues(self, textoutput=True):

        logger.debug("Helios: Reading values of all registers and coils ...")

        varid_groups = {}  # prevent double handling of coil bytes
        measured_values = {}

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

                        if var_name in ["temperature_outdoor_air", "temperature_supply_air", "temperature_extract_air", "temperature_exhaust_air"]:
                            measured_values[var_name] = var_value

                        if var_name == "fault_number":
                            error_text = COMPONENT_FAULTS.get(var_value, "")
                            if textoutput==True:
                                print(f"fault_text: {error_text}")
                            self.GLOBAL_VALUES['fault_text'] = error_text
                    else:
                        logger.warning(f"Failed to resolve value for variable: {var_name}")
                        print(f"{var_name}: Failed to resolve value")
                

                    if all(key in measured_values for key in ["temperature_outdoor_air", "temperature_supply_air", "temperature_extract_air", "temperature_exhaust_air"]):
                        calculated_values = self.calculate_derived_values(measured_values)
                        for calc_name, calc_value in calculated_values.items():
                            if calc_value is not None:
                                self.GLOBAL_VALUES[calc_name] = calc_value
                                logger.debug(f"{calc_name}: {calc_value}")
                                if textoutput:
                                    print(f"{calc_name}: {calc_value}")
                    else:
                        logger.warning(f"Failed to calculate temperatures/efficiency - not all temps available.")

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
    logger.debug(vars(args))

    # use IP and Port from arguments, if provided (otherwise use default)
    ip_address = args.ip
    port = args.port

    # initialize helios connection
    helios = HeliosBase(ip_address, port)

    # start watchdog thread
    stop_event = threading.Event()
    watchdog_thread = threading.Thread(target=watchdog, args=(stop_event,))
    watchdog_thread.start()

    try:
        logger.debug("~~ Starting - waiting for ok from threading")
        with execution_lock:
            logger.debug("Got ok from threading.")
            helios = HeliosBase(ip_address, port)
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
