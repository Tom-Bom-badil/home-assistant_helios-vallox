import socket
import logging
import threading
import time
import argparse
import select
import random

try:
    from .const import ( # HA
        REGISTERS_AND_COILS,
        NTC5K_TEMPERATURES,
        BUS_ADDRESSES,
        FANSPEEDS,
        DEFAULT_IP,
        DEFAULT_PORT,
        COMPONENT_FAULTS
    )
except ImportError:
    from const import ( # Shell / CLI for testing
        REGISTERS_AND_COILS,
        NTC5K_TEMPERATURES,
        BUS_ADDRESSES,
        FANSPEEDS,
        DEFAULT_IP,
        DEFAULT_PORT,
        COMPONENT_FAULTS
    )

class HeliosBase:

    ###### Init ################################################################

    def __init__(self, hass=None, ip=None, port=None, coordinator=None):
        # self.logger = logging.getLogger(__name__)
        self.logger = logging.getLogger("helios_vallox.vent_functions")
        self._hass = hass
        self._ip = ip
        self._port = port
        self._coordinator = coordinator
        self._socket = None
        self._lock = threading.Lock()
        self._all_values, self._cache = {}, {}

    ###### Exposed functions (used from outside) ###############################

    # reads a single variable from the ventilation
    def readSingleValue(self, varname):
        if not self._connect():
            return {}
        self._lock.acquire()
        self._cache.pop(REGISTERS_AND_COILS[varname]["varid"], None)
        try:
            value = self._performRead(varname)
            return {varname: value}
        except Exception as e:
            self.logger.error(f"Exception in _readSingleValue(): {e}")
        finally:
            self._lock.release()
            self._disconnect()

    # reads all known variables from the ventilation
    def readAllValues(self):
        if not self._connect():
            return {}
        self._lock.acquire()
        self._all_values, self._cache = {}, {}
        try:
            start_time = time.time()
            for varname in REGISTERS_AND_COILS:
                value = self._performRead(varname)
                self._all_values[varname] = value
            self._all_values = self._addCalculationsToReadings(self._all_values)
            self.logger.info(f"Full read took {time.time() - start_time:.2f}s.")
            return self._all_values
        except Exception as e:
            self.logger.error(f"Exception in _readAllValues(): {e}")
        finally:
            self._lock.release()
            self._disconnect()

    # writes a single variable to the ventilation, including plausability checks
    def writeValue(self, varname, value):
        if not self._connect() or not self._validateBeforeWrite(varname, value):
            return False
        self._lock.acquire()
        try:
            return self._performWrite(varname, value)
        except Exception as e:
            self.logger.error(f"Exception in _writeValue(): {e}")
        finally:
            self._lock.release()
            self._disconnect()

    ###### Internal functions (higher layers) ##################################

    # read from a single register, cache registers containing single bits ('coils')
    def _performRead(self, varname):
        varid = REGISTERS_AND_COILS[varname]["varid"]
        if REGISTERS_AND_COILS[varname]["type"] == "bit" and varid in self._cache:
            return self._convertFromRaw(varname, self._cache[varid])
        try:
            sender, receiver = BUS_ADDRESSES["_HA"], BUS_ADDRESSES["MB1"]
            retry_count, max_retries = 0, 10
            while retry_count < max_retries:
                if not self._syncWithRS485():
                    return None
                self._sendTelegram(sender, receiver, 0, varid)  # request register
                value = self._receiveTelegram(receiver, sender, varid) # read response
                if value is not None:
                    if REGISTERS_AND_COILS[varname]["type"] == "bit":
                        self._cache[varid] = value
                    if retry_count > 1: # log multiple re-reads (a single one is ok)
                        self.logger.info(f"Retries for {varname}: {retry_count}.")
                    return self._convertFromRaw(varname, value)
                retry_count += 1
                # if there are several HA instances running, reads may overlap each other
                # this blocking results in read times >300s and more - so lets de-sync them
                if retry_count == 5:
                    time.sleep(random.randint(1, 5))
            # give up, too many re-reads
            self.logger.error(f"Failed to read '{varname}' after {retry_count} attempts.")
            return None
        except Exception as e:
            self.logger.error(f"Exception in _performRead(): {e}")
            return None

    def _addCalculationsToReadings(self, all_values):
        # add fault text (if any)
        fault_number = all_values.get('fault_number')
        if fault_number is not None:
            all_values['fault_text'] = COMPONENT_FAULTS.get(fault_number, "-")
        # add heat recovery and efficiency values (all temps required for this)
        keys = {
            'temperature_outdoor_air', 'temperature_supply_air',
            'temperature_extract_air', 'temperature_exhaust_air'
        }
        if keys.issubset(all_values) and all(all_values[k] is not None for k in keys):  
            outdoor_air = all_values['temperature_outdoor_air']
            supply_air = all_values['temperature_supply_air']
            extract_air = all_values['temperature_extract_air']
            exhaust_air = all_values['temperature_exhaust_air']
            temperature_reduction = extract_air - exhaust_air
            temperature_gain = supply_air - outdoor_air
            temperature_balance = temperature_reduction - temperature_gain
            efficiency = 0
            delta = extract_air - outdoor_air
            if delta != 0:  # prevent div/0 if temeperatures are the same
                efficiency = (temperature_gain / delta) * 100
                efficiency = int(max(0, min(efficiency, 100))) # limit to 0..100
            all_values.update({
                'temperature_reduction': temperature_reduction,
                'temperature_gain': temperature_gain,
                'temperature_balance': temperature_balance,
                'efficiency': efficiency
            })
        return all_values

    # write to a single register
    def _performWrite(self, varname, value):
        try:
            # preparations
            vardef = REGISTERS_AND_COILS[varname]
            if vardef["type"] == "bit":
                currentval = self._cache.get(vardef["varid"])
            else:
                currentval = None
            rawvalue = self._convertToRaw(varname, value, currentval)
            if rawvalue is None:
                self.logger.error(f"Writing failed: Cannot convert {value}.")
                return False
            sender, receiver = BUS_ADDRESSES["_HA"], BUS_ADDRESSES["MB1"]
            register = vardef["varid"]
            # the actual write
            self.logger.info(f"Writing {value} to {varname}")
            self._sendTelegram(sender, receiver, register, rawvalue)
            self._all_values[varname] = value   # update entities and bitcache
            if vardef["type"] == "bit":
                self._cache[vardef["varid"]] = rawvalue
            return True
        except Exception as e:
            self.logger.error(f"Exception in _performWrite(): {e}")
            return False

    ###### Internal functions (lower layers) ###################################

    # connect to bus upon start and re-connect if needed
    def _connect(self):
        if self._socket:
            try:
                self._socket.recv(1, socket.MSG_PEEK) # check for active socket
                return True
            except socket.error:
                self.logger.debug("(Re-)connecting to RS485.")
                self._socket.close()
                self._socket = None
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(1.5)
            self._socket.connect((self._ip, self._port))
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024)
            self._socket.setsockopt(socket.SOL_TCP, socket.TCP_USER_TIMEOUT, 1500)
            self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            return True
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self._socket = None
            return False

    # disconnect from bus
    def _disconnect(self):
        if self._socket is not None:
            self.logger.debug("Disconnecting.")
            self._socket.close()
            self._socket = None

    # discover bus silence, return a free sending slot or a timeout
    def _syncWithRS485(self):
        gotSlot = False
        silence_time = 0.007  # free sending slot length
        timeout = time.time() + 1
        while time.time() < timeout:
            ready = select.select([self._socket], [], [], silence_time)
            if ready[0]:
                try:
                    chars = self._socket.recv(1)
                    if chars:  # data received, bus busy
                        continue  # try again
                except socket.error as e:
                    self.logger.error(f"Socket error in _syncWithRS485: {e}")
                    return False
            else:  # bus is quiet, we have a sending slot
                gotSlot = True
                break
        return gotSlot

    # return entity value from a raw int received from the bus
    def _convertFromRaw(self, varname, rawvalue):
        vardef = REGISTERS_AND_COILS[varname]
        conversion_map = {
            "temperature": lambda v: int(NTC5K_TEMPERATURES[v]),
            "fanspeed": lambda v: int(FANSPEEDS.get(v, 1)),
            "bit": lambda v: bool(v >> vardef["bitposition"] & 0x01),
            "dec": lambda v: int(v // 3) if varname == "defrost_hysteresis" else int(v)
        }
        return conversion_map.get(vardef["type"], lambda _: None)(rawvalue)

    # return a raw value from int/bool for writing to the bus
    def _convertToRaw(self, varname, value, currentval):
        vardef = REGISTERS_AND_COILS[varname]
        conversion_map = {
            "temperature": lambda v: int(NTC5K_TEMPERATURES.index(int(v))),
            "fanspeed": lambda v: int({v: k for k, v in FANSPEEDS.items()}.get(int(v), 0)),
            "bit": lambda v: currentval | (1 << vardef["bitposition"]) if str(v).lower() in {"true", "1", "on"} 
                else currentval & ~(1 << vardef["bitposition"]),
            "dec": lambda v: int(v * 3) if varname == "defrost_hysteresis" else int(v)
        }
        return conversion_map.get(vardef["type"], lambda _: None)(value)

    # calculate a telegram checksum (last byte / byte 6 of each telegram)
    def _calculateCRC(self, telegram):
        sum = 0
        for c in telegram[:-1]:
            sum = sum + c
        return sum % 256

    # send a telegram to the RS485 (=register read request or register write)
    def _sendTelegram(self, sender, receiver, register, value):
        telegram = [ 0x01, sender, receiver, register, value, 0 ]
        telegram[5] = self._calculateCRC(telegram)
        if not self._syncWithRS485():
            self.logger.error("Writing failed: No proper connection available.")
        try:
            self._socket.sendall(bytearray(telegram))
            # time.sleep(0.001)
            # self._socket.sendall(bytearray(telegram))
            return True
        except socket.error as e:
            self.logger.error(f"Socket error during send: {e}")
            return False

    # read a telegram from RS485 (called after sending a register read request)
    def _receiveTelegram(self, sender, receiver, register):
        telegram = [0, 0, 0, 0, 0, 0] # FIFO ring buffer
        timeout = time.time() + 1.5
        while time.time() < timeout:
            try:
                char = self._socket.recv(1) # parse each byte received from bus
                if not char:
                    continue
                byte = char[0]
                telegram.pop(0) # delete oldest byte from the left
                telegram.append(byte) # add newly read byte to the right
                if telegram[0] == 0x01: # compare and return value if successful
                    if (telegram[1] == sender and
                        telegram[2] == receiver and
                        telegram[3] == register and
                        telegram[5] == self._calculateCRC(telegram)):
                        return telegram[4]
            except socket.timeout:
                continue
        self.logger.debug("Read timeout.")
        return None

    # Plausibility checks before writing to the bus
    def _validateBeforeWrite(self, varname, value):
        # Check for valid variable name
        if REGISTERS_AND_COILS.get(varname) is None:
            self.logger.error(f"Writing stopped: Invalid variable '{varname}'.")
            return False
        # Prevent writing to register 06h (may cause irrepairable damage)
        if REGISTERS_AND_COILS[varname]["varid"] == 0x06:
            self.logger.critical("Writing stopped: 06h writes are prohibited.")
            return False
        # Prevent writing read-only variables
        if REGISTERS_AND_COILS[varname]["write"] != True:
            self.logger.error(f"Writing stopped: '{varname}' is read-only.")
            return False
        # Make sure value is int or bool
        if not isinstance(value, (int, bool)):
            if REGISTERS_AND_COILS[varname]["type"] == "bit":
                if value in ['1', True, 'True', 'true', 'On', 'on', 'ON'] or \
                value in ['0', False, 'False', 'false', 'Off', 'off', 'OFF']:
                    self.logger.debug(f"Valid bool '{value}' detected.")
                else:
                    self.logger.error(f"Writing stopped: '{value}' is not a bool.")
                    return False
            else:
                self.logger.error(f"Writing stopped: '{value}' is not an integer.")
                return False
        # Check if value is within allowed limits (HA only, not at CLI!)
        if self._hass:
            entity = self._hass.states.get(f"sensor.ventilation_{varname}")
            if entity:
                min_value = entity.attributes.get("min_value")
                max_value = entity.attributes.get("max_value")
                min_value = int(min_value) if isinstance(min_value, (int, float)) else None
                max_value = int(max_value) if isinstance(max_value, (int, float)) else None
                self.logger.debug(f"Validating '{varname}': value={value}, min={min_value}, max={max_value}")
                if min_value is not None and int(value) < min_value:
                    self.logger.error(f"Writing stopped: {value} below min of {min_value}.")
                    return False
                if max_value is not None and int(value) > max_value:
                    self.logger.error(f"Writing stopped: {value} above max of {max_value}.")
                    return False
        return True

###### for CLI (command line) testing only #####################################

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
        value = helios.readSingleValue(args.read)
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
