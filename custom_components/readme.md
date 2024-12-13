Bisher nur Kommentare:

--------------------

service: ventilation.write_value
data:
  variable: "fanspeed"
  value: 3

-------------------


This is the HA-adaption of my Python script that used to work in my old home automation system for >10 years.
During that time, users have confirmed that the following models are compatible to the protocol implemented in this custom component:

Helios EC 200 Pro R/L
Helios EC 200 Pro R/L
Vallo Plus 510 SE
Vallo Plus 350SE
Vallox 910SE
Vallox 090 SE
Vallox Digit SE
Vallox 130D (not all registers reported working or with same number, see below)

The protocol used by those ventilation devices is Modbus-like; however, it is *not exactly* Modbus, so an individual implementation is required.


--------------
Vallox 130D:
"outside_temp"    : {"varid" : 0x58, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },#working
"exhaust_temp"    : {"varid" : 0x5c, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },#working
"inside_temp"     : {"varid" : 0x5A, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },#working
"incoming_temp"   : {"varid" : 0x5B, 'type': 'temperature',  'bitposition': -1, 'read': True, 'write': False },#working 
--------------



---
Ich glaube, hier ist noch etwas verkehrt, am Beispiel Schreiben der fanspeed:

2015-01-05 23:50:28,866 - root - DEBUG - Helios: Connecting...
2015-01-05 23:50:28,947 - root - DEBUG - Helios: Sending telegram '0x01 0x2F 0x20 0x29 0x03 0x7C'
2015-01-05 23:50:28,951 - root - DEBUG - Helios: Sending telegram '0x01 0x2F 0x10 0x29 0x03 0x6C'
2015-01-05 23:50:28,954 - root - DEBUG - Helios: Sending telegram '0x01 0x2F 0x11 0x29 0x03 0x6D'
2015-01-05 23:50:28,958 - root - DEBUG - Helios: Sending telegram '0x6D'
2015-01-05 23:50:28,962 - root - DEBUG - HeliosBase: Disconnecting...

Das letzte 0x6D muss man als Quittung von der 0x11 empfangen, nicht senden. Steht so auch in der Vallox-Doku. Die 0x20 und 0x10 senden hingegen keine Quittungen, daher ist hier nichts zu tun.
---