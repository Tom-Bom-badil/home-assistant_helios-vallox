import logging
import socket
import threading
import time
import array
import json
import argparse

# Log-Einstellungen
logging.basicConfig(
    filename='helios.log',  # Logdatei
    # level=logging.DEBUG,    # Loglevel
    level=logging.INFO,    # Loglevel
    format='%(asctime)s - %(levelname)s - %(message)s'  # Logformat
)
logger = logging.getLogger("")


# Threading-Einstellungen
execution_lock = threading.Lock()
operation_timeout = 50  # Maximal erlaubte Zeit für das Script in Sekunden
def watchdog(stop_event):
    """Watchdog beendet das Skript, wenn die operation_timeout überschritten wird."""
    if not stop_event.wait(operation_timeout):
        logger.error("Watchdog: Timeout überschritten. Script wird abgebrochen.")
        raise TimeoutError("Maximale Ausführungszeit überschritten.")


# Netzwerkeinstellungen des LAN-RS485 Konverters
DEFAULT_IP = "192.168.178.38"
DEFAULT_PORT = 8234


# Mapping für Sender und Empfänger
BUS_ADDRESSES = {
    "MB*": 0x10,  # alle Mainboards
    "MB1": 0x11,  # Mainboard 1
    "FB*": 0x20,  # alle Fernbedienungen
    "FB1": 0x21,  # Fernbedienung 1
    "LON": 0x28,  # LON Bus Modul
    "_HA": 0x2E,  # dieses Python Script
    "_SH": 0x2F   # SmartHomeNG Python Script
}


# Mapping für Temperaturen
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

# Mapping für Lüftungsstufe
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

# Mapping für Fehlermeldungen
COMPONENT_FAULTS = {
    5: 'Inlet air sensor fault',
    6: 'CO2 Alarm',
    7: 'Outside air sensor fault',
    8: 'Exhaust air sensor fault',
    9: 'Water coil frost warning',
    10: 'Outlet air sensor fault'
}

# Mapping für Register
REGISTERS_AND_COILS = {
    # Aktuelle Lüftungsstufe (EC300Pro: 1..8)
    "fanspeed"          : {"varid" : 0x29, 'type': 'fanspeed',     'bitposition': -1, 'read': True, 'write': True  },
    # Automatische Lüftungsstufe nach dem Einschalten
    "initial_fanspeed"  : {"varid" : 0xA9, 'type': 'fanspeed',     'bitposition': -1, 'read': True, 'write': True  },
    # Maximal einstellbare Lüftungsstufe
    "max_fanspeed"      : {"varid" : 0xA5, 'type': 'fanspeed',     'bitposition': -1, 'read': True, 'write': True  },
    # NTC5K Sensoren in der KWL
    # Temperatur Frischluft
    "outside_temp"      : {"varid" : 0x32, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },
    # Temperatur Zuluft
    "inlet_temp"        : {"varid" : 0x35, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },
    # Temperatur Abluft
    "outlet_temp"       : {"varid" : 0x34, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },
    # Temperatur Fortluft
    "exhaust_temp"      : {"varid" : 0x33, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },
    # verschiedene Coils im Register 0xA3 mit Statusanzeigen auf den Fernbedienungen (0..3 read/write, 4..7 readonly)
    # FB LED1: KWL an/aus; Achtung: Fernbedienungen schalten nicht automatisch an; fanspeed=initial_fanspeed bei 'on'
    "powerstate"        : {"varid" : 0xA3, 'type': 'bit',          'bitposition':  0, 'read': True, 'write': True  },
    # FB LED2: CO2
    "co2_indicator"     : {"varid" : 0xA3, 'type': 'bit',          'bitposition':  1, 'read': True, 'write': False },
    # FB LED3: Luftfeuchte
    "rh_indicator"      : {"varid" : 0xA3, 'type': 'bit',          'bitposition':  2, 'read': True, 'write': False },
    # FB LED4: 0 = Sommermodus mit Bypass, 1 = Wintermodus mit Wärmerückgewinnung (LED ist im Wintermodus an)
    "summer_winter_mode": {"varid" : 0xA3, 'type': 'bit',          'bitposition':  3, 'read': True, 'write': False },
    # FB Anzeige 1: Filterwarnung
    "clean_filter"      : {"varid" : 0xA3, 'type': 'bit',          'bitposition':  4, 'read': True, 'write': False },
    # FB Anzeige 2: Nachheizung aktiv
    "post_heating_on"   : {"varid" : 0xA3, 'type': 'bit',          'bitposition':  5, 'read': True, 'write': False },
    # FB Anzeige 3: Fehleranzeige
    "fault_detected"    : {"varid" : 0xA3, 'type': 'bit',          'bitposition':  6, 'read': True, 'write': False },
    # FB Anzeige 4: Serviceanzeige
    "service_requested" : {"varid" : 0xA3, 'type': 'bit',          'bitposition':  7, 'read': True, 'write': False },
    # Ab dieser Temperatur im Sommermodus: Wenn Abluft (innen) > Frischluft (außen), dann Bypass aktivieren
    "bypass_setpoint"   : {"varid" : 0xAF, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': True  },
    # Einschalttemperatur Vorheizung
    "preheat_setpoint"  : {"varid" : 0xA7, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': True  },
    # Vorheizung aus (0) / ein (1)
    "preheat_status"    : {"varid" : 0x70, 'type': 'bit',          'bitposition':  7, 'read': True, 'write': True  },
    # Frostschutz - unterhalb dieser Temperatur Frischluftventilator und Vorheizung aus; -6 ... +15°C
    "defrost_setpoint"  : {"varid" : 0xA8, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': True  },
    # Frostschutztemperatur + dieser Wert = Ventilator wieder ein (Hysterese); Wert / 3 entspricht ca 1°C
    "defrost_hysteresis": {"varid" : 0xB2, 'type': 'dec_special',  'bitposition': -1, 'read': True, 'write': True  },
    # Stoßlüftungs-Modus: 0=Kaminlüftung ("Anheizen - Abluft in den ersten 15 Minuten aus"), 1=Stoßlüftung
    "boost_mode"        : {"varid" : 0xAA, 'type': 'bit',          'bitposition':  5, 'read': True, 'write': True  },
    # Einschalter 45 Minuten Stoßlüftung / Maximalstufe (für Boost auf 1 setzen; Anlage setzt selbstständig zurück)
    "boost_on_switch"   : {"varid" : 0x71, 'type': 'bit',          'bitposition':  5, 'read': True, 'write': True  },
    # Aktueller Status der Stoßlüftung (aus/an)
    "boost_status"      : {"varid" : 0x71, 'type': 'bit',          'bitposition':  6, 'read': True, 'write': False },
    # Verbleibende Minuten bei aktivierter Stoßlüftung
    "boost_remaining"   : {"varid" : 0x79, 'type': 'dec',          'bitposition': -1, 'read': True, 'write': False },
    # Ausschaltregister Zuluftventilator (1=aus); u.a. vom Frostschutz benutzt; muss ggf. zweifach beschrieben werden
    "input_fan_off"     : {"varid" : 0x08, 'type': 'bit',          'bitposition':  3, 'read': True, 'write': True  },
    # Ausschaltregister Abluftventilator (1=aus); muss ggf. zweifach beschrieben werden
    "output_fan_off"    : {"varid" : 0x08, 'type': 'bit',          'bitposition':  5, 'read': True, 'write': True  },
	# Voreinstellwert für die Motordrehzahl des Zuluftventilators (65...100% - Drosselung / pneumatischer Abgleich)
    "input_fan_percent" : {"varid" : 0xB0, 'type': 'dec',          'bitposition': -1, 'read': True, 'write': True  },
	# Voreinstellwert für die Motordrehzahl des Abluftventilators (65...100% - Drosselung / pneumatischer Abgleich)
    "output_fan_percent": {"varid" : 0xB1, 'type': 'dec',          'bitposition': -1, 'read': True, 'write': True  },   
    # Voreinstellung für Intervall der Service-Erinnerung (Filterwechsel) nach Zurücksetzen in Monaten
    "service_interval"  : {"varid" : 0xA6, 'type': 'dec',          'bitposition': -1, 'read': True, 'write': True  },
    # Restzeit bis zum nächsten Filterwechsel in Monaten
    "service_due_months": {"varid" : 0xAB, 'type': 'dec',          'bitposition': -1, 'read': True, 'write': True  },
    # Fehlerregister - 0 = kein Fehler; siehe COMPONENT_FAULTS
    "fault_number"      : {"varid" : 0x36, 'type': 'dec',          'bitposition': -1, 'read': True, 'write': False }
}


class HeliosException(Exception):
    pass


class HeliosBase():

    def __init__(self, ip=DEFAULT_IP, port=DEFAULT_PORT):
        self._ip = ip
        self._port = port
        self._is_connected = False
        self._socket = None
        self._lock = threading.Lock() # Threading-Überwachung gegen Mehrfachausführung
        self.GLOBAL_VALUES = {}  # Lokales Dictionary nur für diesen Thread


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
        """Sende ein Telegramm und logge den Inhalt."""
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
                    # Jitter-Handhabung: Ignoriere Telegramme, die nicht mit dem Startbyte 0x01 beginnen, aber logge sie
                    if buffer[0] != 0x01:
                        logger.warning(f"Ignoring jitter data: {' '.join(f'{byte:02X}' for byte in buffer)}")
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


    def _waitForBusQuiet(self):
        """
        Wartet, bis mindestens 10 ms keine Aktivität auf dem RS485-Bus stattgefunden hat.
        Überwacht die Busaktivität durch den Empfang von Daten.
        """
        logger.debug("Helios: Waiting for bus silence...")
        got_slot = False
        backup_timeout = self._socket.gettimeout()  # Sichere den aktuellen Timeout
        self._socket.settimeout(0.01)  # Überwachung mit kurzen Zeitfenstern

        try:
            end = time.time() + 3  # Maximal 3 Sekunden auf Ruhe warten
            last_activity = time.time()

            while end > time.time():
                try:
                    data = self._socket.recv(1)  # Versuche, ein Byte zu lesen
                    if data:
                        # Aktivität festgestellt, aktualisiere Zeit
                        last_activity = time.time()
                    else:
                        # Keine Daten: Prüfe, ob 10 ms vergangen sind
                        if time.time() - last_activity > 0.01:  # 10 ms Ruhezeit
                            got_slot = True
                            break
                except socket.timeout:
                    # Timeout ohne Daten → Ruhephase erkannt
                    if time.time() - last_activity > 0.01:  # 10 ms Ruhezeit
                        got_slot = True
                        break
        except Exception as e:
            logger.error(f"Helios: Error while waiting for bus silence: {e}")
        finally:
            self._socket.settimeout(backup_timeout)  # Ursprünglichen Timeout wiederherstellen

        if not got_slot:
            logger.warning("Helios: Bus silence not achieved within 3 seconds.")
        return got_slot


    def readValue(self, varname, retries=3):
        """Liest einen Wert vom Bus mit Synchronisation für RS485."""
        for attempt in range(retries):
            if not self._is_connected:
                logger.error("Helios: Not connected.")
                return None
            try:
                # Warte auf Busruhe
                if not self._waitForBusQuiet():
                    logger.error("Helios: Bus not silent, cannot read value.")
                    continue

                var_id = REGISTERS_AND_COILS[varname]["varid"]
                telegram = self._createTelegram(BUS_ADDRESSES["_HA"], BUS_ADDRESSES["MB1"], 0, var_id)
                self._sendTelegram(telegram)

                # Warte auf Busruhe vor Empfang
                if not self._waitForBusQuiet():
                    logger.error("Helios: Bus not silent before receiving data.")
                    continue

                value = self._readTelegram(BUS_ADDRESSES["MB1"], BUS_ADDRESSES["_HA"], var_id)
                if value is not None:
                    return value

            except Exception as e:
                logger.error(f"Helios: Error in readValue (Attempt {attempt + 1}): {e}")
            time.sleep(0.05)  # Kurze Pause vor dem nächsten Versuch
        logger.error(f"Helios: Failed to read value for variable {varname} after {retries} retries.")
        return None


    def prepare_value_for_write(self, varname, value):
        """
        Bereitet den Wert für das Schreiben entsprechend dem Variablentyp vor.
        - temperature: Index aus NTC5K_TEMPERATURES
        - fanspeed: Zuordnung aus FANSPEEDS
        - bit: Setzt das Bit an der korrekten Position im Byte
        - dec: normale Zahl (int)
        - dec_special: Spezialbehandlung für Register 0xB2, 03h=1°C
        """

        if varname not in REGISTERS_AND_COILS:
            raise ValueError(f"Variable '{varname}' is not defined in REGISTERS_AND_COILS.")

        var_info = REGISTERS_AND_COILS[varname]
        
        if var_info["type"] == "temperature":
            return NTC5K_TEMPERATURES.index(value)   # Index wird geschrieben
            
        elif var_info["type"] == "fanspeed":
            return {v: k for k, v in FANSPEEDS.items()}[value]   # Rückwärtsmapping

        elif var_info["type"] == "bit":
            current_value = self.readValue(varname)
            bit_pos = var_info["bitposition"]
            if value:
                return current_value | (1 << bit_pos)  # Setzen des Bits
            else:
                return current_value & ~(1 << bit_pos)  # Löschen des Bits
            
        elif var_info["type"] == "dec":
            return value   # Dezimalwert direkt zurückgeben

        elif var_info["type"] == "dec_special":
            return value * 3    # Wert mit 3 multiplizieren


    def writeValue(self, varname, value):
        """Schreibt einen Wert auf den Bus mit Sicherheitsüberprüfungen und Typkonvertierung."""

        if not self._is_connected:
            logger.error("Helios: Not connected, cannot write register.")
            return False

        # Überprüfe, ob die Variable existiert und beschrieben werden darf
        if varname not in REGISTERS_AND_COILS:
            logger.error(f"Variable '{varname}' ist nicht definiert.")
            return False

        var_info = REGISTERS_AND_COILS[varname]
        if not var_info.get("write", False):
            logger.error(f"Variable '{varname}' ist nicht schreibbar.")
            return False

        # Prüfe, ob das Zielregister 0x06 ist (kritische Sicherheitsfunktion)
        if var_info['varid'] == 0x06:
            logger.critical("Helios: Attempted to write to register 0x06. Operation aborted to prevent system damage.")
            return False

        # Wert vorbereiten
        formatted_value = self.prepare_value_for_write(varname, value)
        logger.debug(f"Starting to write {value}/{formatted_value} into {varname}.")


        for target in ["FB*", "MB*", "MB1"]:
            
            # Erstelle das Telegramm
            telegram = [
                0x01,
                BUS_ADDRESSES["_HA"],
                BUS_ADDRESSES[target],
                var_info["varid"],
                formatted_value,
                0
            ]
            telegram[5] = self._calculateCRC(telegram)

            # Warte auf Busruhe vor dem Schreiben
            if not self._waitForBusQuiet():
                logger.error("Bus nicht ruhig vor Schreibvorgang.")
                return False

            #----------------------------------------------------------------#
            if not self._sendTelegram(telegram):
                logger.error(f"Helios: Failed write variable '{varname}'.")
                return False

            if target == "MB1":
                crc_telegram = [telegram[5]]
                self._sendTelegram(crc_telegram)
                logger.debug(f"Resent CRC to Mainboard to finalize writing.")
            #-----------------------------------------------------------------#

        logger.debug(f"Writing successful.")
        return True


    def resolve_variable(self, varid, data_byte):
        """
        Ermittelt die Variable basierend auf der ID und interpretiert sie.
        Stellt sicher, dass jede Variable nur einmal ausgegeben wird.
        """
        results = []
        processed_bits = set()  # Verwendet zur Verfolgung von verarbeiteten Bitpositionen

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
                    fanspeed = FANSPEEDS.get(data_byte, "Unbekannt")
                    results.append((var_name, fanspeed))
                elif var_type == "dec":
                    results.append((var_name, data_byte))
                elif var_type == "dec_special":
                    results.append((var_name, data_byte))
        return results  # Rückgabe eindeutiger Variablen


    def readAllValues(self, textoutput=True):
        """Liest alle bekannten Variablen, gruppiert nach varid, und aktualisiert das globale Dictionary."""
        logger.debug("Helios: Reading all variable values...")

        # Gruppiere Variablen nach varid, um doppelte Anfragen zu vermeiden
        varid_groups = {}
        for varname, details in REGISTERS_AND_COILS.items():
            varid = details["varid"]
            if varid not in varid_groups:
                varid_groups[varid] = []
            varid_groups[varid].append(varname)

        # Sende eine Anfrage pro varid und bearbeite alle zugehörigen Variablen
        for varid, varnames in varid_groups.items():
            self._waitForBusQuiet()  # Warte auf Ruhe vor der Anfrage
            time.sleep(0.02)  # 50 ms Pause zwischen Anfragen
            value = self.readValue(varnames[0])  # Nutze die erste Variable nur zur Anfrage
            if value is not None:
                # Auflösen aller zugehörigen Variablen
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

    # Argumentparser für die Parameter
    parser = argparse.ArgumentParser(description="Helios RS485 Steuerung")
    parser.add_argument("--read_all", action="store_true", help="Liest alle bekannten Variablen (Standardverhalten). Ausgabe zeilenweise als Text.")
    parser.add_argument("--dict", action="store_true", help="Wie --read_all, aber Ausgabe als Dictionary.")
    parser.add_argument("--json", action="store_true", help="Wie --read_all, aber Ausgabe als JSON.")
    parser.add_argument("--read_value", nargs=1, metavar="VARIABLE", help="Liest den Wert einer spezifischen Variablen.")
    parser.add_argument("--write_value", nargs=2, metavar=("VARIABLE", "WERT"), help="Schreibt einen Wert in eine spezifische Variable.")

    args = parser.parse_args()

    # Starte den Watchdog-Thread
    stop_event = threading.Event()
    watchdog_thread = threading.Thread(target=watchdog, args=(stop_event,))
    watchdog_thread.start()

    try:
        logger.debug("Waiting for ok from threading ...")
        with execution_lock:  # Sperre blockiert, bis sie verfügbar ist
            logger.debug("Got it.")
            helios = HeliosBase()
            if helios.connect():
                logger.debug(f"Connected to Helios - {helios._ip}:{helios._port}")

                if args.read_all or not (args.read_value or args.write_value):

                    # Standardverhalten: Alle Werte, Ausgabe als Text
                    if not (args.dict or args.json):
                        helios.readAllValues()
                    
                    # Alle Werte, Ausgabe als Dictionary
                    if args.dict:
                        helios.readAllValues(textoutput=False)
                        GLOBAL_VALUES = helios.get_global_values()
                        print(GLOBAL_VALUES)
                        
                    # Alle Werte, Ausgabe als JSON
                    if args.json:
                        helios.readAllValues(textoutput=False)
                        GLOBAL_VALUES = helios.get_global_values()
                        print(json.dumps(GLOBAL_VALUES, indent=4))

                if args.read_value:
                    variable = args.read_value[0]
                    value = helios.readValue(variable)
                    if value is not None:
                        # Konvertierten Wert ausgeben
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
                        print(f"{variable}: {converted_value}")
                    else:
                        logger.error(f"Failed to read value for {variable}.")

                if args.write_value:
                    variable, raw_value = args.write_value
                    try:
                        value = int(raw_value)  # Konvertiere den Wert in eine Zahl
                        if helios.writeValue(variable, value):
                            print(f"Successfully wrote {value} to {variable}.")
                        else:
                            logger.error(f"Failed to write {value} to {variable}")
                    except ValueError:
                        logger.error(f"Invalid value provided for {variable}: {raw_value}")

                helios.disconnect()
                logger.debug("Disconnected from Helios.")

                
                # Testszenario: Werte schreiben

                # ok:  type temperature - 10 (default) / 12
                #helios.writeValue("bypass_setpoint", 10)
                #time.sleep(2)
                
                # ok:  type fanspeed - 2 / 4
                #helios.writeValue("fanspeed", 4)
                #time.sleep(2)
                
                # ok: type dec - 0 / 2
                #helios.writeValue("service_due_months", 0)
                #time.sleep(2)

                # ok: dec_special 3 (default) / 2
                #helios.writeValue("defrost_hysteresis", 2)
                #time.sleep(2)

                # ok: bit 0 / 1 (default)
                # helios.writeValue("boost_mode", 1)
                # time.sleep(2)

                # ok - Beispiel: Lesen aller Werte
                #helios.readAllValues()
                #GLOBAL_VALUES = helios.get_global_values()
                #logger.debug(f"Global values: {GLOBAL_VALUES}")

                # nur zur Kontrolle:
                #print(f"Global values: {GLOBAL_VALUES}")

    except TimeoutError as te:
        print(f"Error: {te}")
    finally:
        stop_event.set()  # Signalisiert dem Watchdog, dass die Arbeit beendet ist
        watchdog_thread.join()  # Warte auf das Ende des Watchdog-Threads


if __name__ == "__main__":
    main()
