import socket
import logging
import threading
import time
import argparse
import select

try: # HA
    from .const import (
        REGISTERS_AND_COILS,
        NTC5K_TEMPERATURES,
        BUS_ADDRESSES,
        FANSPEEDS,
        DEFAULT_IP,
        DEFAULT_PORT,
        COMPONENT_FAULTS )

except ImportError: # shell / command line
    from const import (
        REGISTERS_AND_COILS,
        NTC5K_TEMPERATURES,
        BUS_ADDRESSES,
        FANSPEEDS,
        DEFAULT_IP,
        DEFAULT_PORT,
        COMPONENT_FAULTS )


class HeliosBase:

    ###### Init

    def __init__(self, ip, port):
        self.logger = logging.getLogger(__name__)
        self._ip = ip
        self._port = port
        self._is_connected = False
        self._socket = None
        self._lock = threading.Lock()
        self._cache = {}
        self._all_values = {}


    ###### Exposed functions (read from outside) ###############################


    def readValue(self, varname):
        if not self._connect():
            self.logger.error(f"Helios: Could not connect to the device.")
            return None
        value = self._readVal(varname)
        self._disconnect()
        if value is not None:
            return {varname: value}
        return None


    def readAllValues(self):
        if not self._connect():
            self.logger.error(f"Helios: Could not connect to the device.")
            return None
        try:
            start_time = time.time()
            self._all_values = {}
            self._cache = {}
            for varname in REGISTERS_AND_COILS.keys():
                value = self._readVal(varname)
                if value is not None:
                    self._all_values[varname] = value
                else:
                    self.logger.error(f"Failed to read value for '{varname}'")
            self._all_values = self._add_calculations(self._all_values)
            end_time = time.time()
            self.logger.info("Full read took {:.2f}s.".format(end_time - start_time))
            self.logger.debug(f"Cache contains: {self._cache}. All read values: {self._all_values}.")
        finally:
            self._disconnect()
        return self._all_values


    def writeValue(self, varname, value):
        if not self._connect():
            self.logger.error(f"Could not connect to the ventilation device.")
            return None
        if not self._check_value(varname, value):
            self.logger.error(f"Write operation cancelled, invalid value.")
            return False
        if REGISTERS_AND_COILS.get(varname) is None:
            self.logger.error(f"Write operation cancelled, invalid variable.")
            return False
        try:
            self.logger.info("Writing {0} to {1}".format(value, varname))
            success = False
            self._lock.acquire()
            try:
                rawvalue = None
                if REGISTERS_AND_COILS[varname]["type"] == "bit":
                    currentval = self._cache[REGISTERS_AND_COILS[varname]["varid"]]
                    if currentval is None:
                        self.logger.error("Writing failed. Cannot read {varname} from cache.")
                        return False
                    rawvalue = self._convertToRaw(varname, value, currentval)
                else:
                    rawvalue = self._convertToRaw(varname, value, None)
                if self._syncWithRS485():
                    if rawvalue is not None:
                        telegram = self._createTelegram(
                            BUS_ADDRESSES["_HA"], BUS_ADDRESSES["MB1"], 
                            REGISTERS_AND_COILS[varname]["varid"], rawvalue
                        )
                        self._sendTelegram(telegram)
                        self.logger.debug("Telegram sent: {0}".format(self._telegramToString(telegram)))

                        self._all_values[varname] = value
                        if REGISTERS_AND_COILS[varname]["type"] == "bit":
                            self._cache[REGISTERS_AND_COILS[varname]["varid"]] = rawvalue

                        success = True
                    else:
                        self.logger.error("Writing failed. Cannot convert value '{0}'.".format(value))
                        success = False
                else:
                    self.logger.error("Writing failed. No free slot for sending telegrams.")
                    success = False
            except Exception as e:
                self.logger.error("Exception in writeValue(): {0}".format(e))
            finally:
                self._lock.release()
        finally:
            self._disconnect()
        return success


    ###### Internally used functions ###########################################


    def _connect(self):
        if self._is_connected:
            return True
        try:
            self.logger.debug("Connecting to {}:{}".format(self._ip, self._port))
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(10)
            self._socket.connect((self._ip, self._port))
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self._is_connected = True
            return True
        except Exception as e:
            self.logger.error("Could not connect to {}:{}. Error: {}".format(self._ip, self._port, e))
            return False


    def _disconnect(self):
        if self._is_connected and self._socket:
            self.logger.debug("Disconnecting.")
            self._socket.close()
            self._is_connected = False


    def _get_entity(self, varname):
        pass


    def _calculateCRC(self, telegram):
        sum = 0
        for c in telegram[:-1]:
            sum = sum + c
        return sum % 256


    def _telegramToString(self, telegram):
        return ' '.join(['0x%0*X' % (2, c) for c in telegram])


    def _convertFromRaw(self, varname, rawvalue):
        vardef = REGISTERS_AND_COILS[varname]
        if vardef["type"] == "temperature":
            return int(NTC5K_TEMPERATURES[rawvalue])
        elif vardef["type"] == "fanspeed":
            return int(FANSPEEDS.get(rawvalue))
        elif vardef["type"] == "bit":
            return bool(rawvalue >> vardef["bitposition"] & 0x01)
        elif vardef["type"] == "dec":
            if varname == "defrost_hysteresis":
                rawvalue = rawvalue // 3
            return int(rawvalue)
        return None


    def _convertToRaw(self, varname, value, currentval):
        vardef = REGISTERS_AND_COILS[varname]
        if vardef['type'] == "temperature":
            return int(NTC5K_TEMPERATURES.index(int(value)))
        elif vardef["type"] == "fanspeed":
            return int({v: k for k, v in FANSPEEDS.items()}.get(int(value)))
        elif vardef["type"] == "bit":
            if value in (True, 1, "true", "True", "1", "On", "on"):
                return currentval | (1 << vardef["bitposition"])
            return currentval & ~(1 << vardef["bitposition"])
        elif vardef["type"] == "dec":
            if varname == "defrost_hysteresis":
                return int(value*3)
        return None


    def _createTelegram(self, sender, receiver, function, value):
        telegram = [1, sender, receiver, function, value, 0]
        telegram[5] = self._calculateCRC(telegram)
        return telegram


    def _sendTelegram(self, telegram):
        if not self._is_connected:
            return False
        self.logger.debug("Helios: Sending telegram '{0}'".format(self._telegramToString(telegram)))
        self._socket.sendall(bytearray(telegram))
        return True


    def _readTelegram(self, sender, receiver, datapoint):
        timeout = time.time() + 0.03     # Stellschraube für lange re-reads
        telegram = [0, 0, 0, 0, 0, 0]
        all_bytes_received = []
        protocol_count = 0
        max_count = 16
        while time.time() < timeout and protocol_count < max_count:
            telegram = [0, 0, 0, 0, 0, 0]
            while self._is_connected and time.time() < timeout:
                try:
                    char = self._socket.recv(1)
                    if len(char) > 0:
                        byte = bytearray(char)[0]
                        all_bytes_received.append(byte)
                        telegram.pop(0)
                        telegram.append(byte)
                        if telegram[0] == 0x01:
                            protocol_count += 1
                            if (telegram[1] == sender and 
                                telegram[2] == receiver and 
                                telegram[3] == datapoint and 
                                telegram[5] == self._calculateCRC(telegram)):
                                self.logger.debug("Telegram received '{0}'".format(self._telegramToString(telegram)))
                                return telegram[4]
                except socket.timeout:
                    self.logger.info("Communication error - socket timeout.")
                    return None
        self.logger.debug("Timeout while awaiting answer - bus busy.")
        self.logger.debug("Protocols received: '{0}'".format(self._telegramToString(all_bytes_received)))
        return None


    def _syncWithRS485(self):
        start_time = time.time()
        gotSlot = False
        end = time.time() + 3
        while time.time() < end:
            ready = select.select([self._socket], [], [], 0.007)
            if ready[0]:
                try:
                    chars = self._socket.recv(1)
                    if len(chars) > 0:   # bus busy
                        end = time.time() + 3
                except socket.error as e:
                    self.logger.error(f"Socket error occurred: {e}")
                    break
            else:  # silence on bus
                gotSlot = True
                break
        return gotSlot


    def _readVal(self, varname):
        varid = REGISTERS_AND_COILS[varname]["varid"]
        value = None
        if REGISTERS_AND_COILS[varname]["type"] == "bit" and varid in self._cache:
            return self._convertFromRaw(varname, self._cache[varid])
        def attempt_read():
            max_retries = 10
            for attempt in range(max_retries-1):
                if self._syncWithRS485():
                    telegram = self._createTelegram(
                        BUS_ADDRESSES["_HA"], BUS_ADDRESSES["MB1"], 0, varid
                    )
                    self._sendTelegram(telegram)
                    value = self._readTelegram(
                        BUS_ADDRESSES["MB1"], BUS_ADDRESSES["_HA"], varid
                    )
                    if value is not None:
                        # Cache bit values:
                        if REGISTERS_AND_COILS[varname]["type"] == "bit":
                            self._cache[varid] = value
                        return self._convertFromRaw(varname, value)
                    else:
                        self.logger.info(f"Reading '{varname}' again ({attempt + 1})")
                        time.sleep(0.05)
                else:
                    self.logger.warning("Reading failed. No free sending slot found.")
            return None
        self._lock.acquire()
        try:
            value = attempt_read()
            if value is None:
                self.logger.error(f"Failed to read value for '{varname}'.")
        except Exception as e:
            self.logger.error("Exception in _readVal(): {0}".format(e))
        finally:
            self._lock.release()
        return value


    def _check_value(self, varname, value):
        # Prevent writing to register 06h (may cause irrepairable damage)
        if REGISTERS_AND_COILS[varname]["varid"] == 0x06:
            self.logger.critical("Writing to register 06h is prohibited. Write operation aborted.")
            return False
        # Prevent writing read-only variables
        if REGISTERS_AND_COILS[varname]["write"] != True:
            self.logger.critical(f"Variable {varname} is read-only and cannot be written to.")
            return False
        # Make sure value is int or bool
        if not isinstance(value, int):
            if REGISTERS_AND_COILS[varname] ["type"] == "bit":
                if  value in [1, '1', True, true, 'True', 'true', 'On', 'on', 'ON'] or \
                    value in [0, '0', False, false, 'False', 'false', 'Off', 'off', 'OFF']:
                    self.logger.debug(f"Valid bool {value} for {varname} detected.")
                else:
                    self.logger.error(f"Value {value} for {varname} is not a valid binary.")
                    return False
            else:
                self.logger.error(f"Invalid value {value} for {varname}, expected an integer.")
                return False
        # Check for value limits min/max
        entity = self._get_entity(varname)
        min_value = getattr(entity, 'min_value', None)
        if min_value is not None and value < min_value:
            self.logger.error(f"Value {value} for {varname} is below the minimum of {min_value}.")
            return False
        max_value = getattr(entity, 'max_value', None)
        if max_value is not None and value > max_value:
            self.logger.error(f"Value {value} for {varname} is above the maximum of {max_value}.")
            return False
        return True


    def _add_calculations(self, all_values):
        fault_number = all_values.get('fault_number')
        if fault_number is not None:
            all_values['fault_text'] = COMPONENT_FAULTS.get(fault_number, "-")

        required_temps = [
            'temperature_outdoor_air', 
            'temperature_supply_air', 
            'temperature_extract_air', 
            'temperature_exhaust_air'
        ]
        if all(temp in all_values for temp in required_temps):
            outdoor_air = all_values['temperature_outdoor_air']
            supply_air = all_values['temperature_supply_air']
            extract_air = all_values['temperature_extract_air']
            exhaust_air = all_values['temperature_exhaust_air']

            # Perform calculations
            temperature_reduction = extract_air - exhaust_air
            temperature_gain = supply_air - outdoor_air
            temperature_balance = temperature_reduction - temperature_gain
            efficiency = None
            delta = extract_air - outdoor_air
            if delta == 0: # would div/0
                efficiency = 0
            elif delta > 0:
                efficiency = (temperature_gain / delta) * 100
            else:
                efficiency = 0
            if efficiency is not None:
                efficiency = int(max(0, min(efficiency, 100)))

            all_values['temperature_reduction'] = temperature_reduction
            all_values['temperature_gain'] = temperature_gain
            all_values['temperature_balance'] = temperature_balance
            all_values['efficiency'] = efficiency

        return all_values


# command line testing only
def main():
    parser = argparse.ArgumentParser(description="Test HeliosBase functions")
    parser.add_argument("--ip", type=str, default=DEFAULT_IP, help="IP address of the device")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port of the device")
    parser.add_argument("--read", type=str, help="Variable name to read")
    parser.add_argument("--readall", action="store_true", help="Read all values")
    parser.add_argument("--write", nargs=2, metavar=("varname", "value"), help="Variable name and value to write")
    args = parser.parse_args()
    helios = HeliosBase(args.ip, args.port)
    if args.read:
        value = helios.readValue(args.read)
        print(value)
    elif args.readall:
        values = helios.readAllValues()
        print(values)
    elif args.write:
        varname, value = args.write
        vardef = REGISTERS_AND_COILS.get(varname)
        if vardef is not None:
            if vardef["type"] == "bit" or vardef["type"] == "dec" or vardef["type"] == "fanspeed":
                value = int(value)
            elif vardef["type"] == "temperature":
                value = float(value)
        if helios.writeValue(varname, value):
            print(f"Successfully wrote {value} to {varname}")
        else:
            print(f"Failed to write {value} to {varname}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
