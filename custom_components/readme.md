This is the HA-adaption of my Python script that used to work in my old home automation system for >10 years.
During that time, users have confirmed that the following models are compatible to the protocol implemented in this custom component:

- Helios EC 200 Pro R/L
- Helios EC 200 Pro R/L
- Vallo Plus 510 SE
- Vallo Plus 350SE
- Vallox 910SE
- Vallox 090 SE
- Vallox Digit SE
- Vallox 130D (not all registers reported working or with same number, see below)

The protocol we are utilizing for this custom integration is Modbus-like; however, it is *not exactly* Modbus, so an individual implementation is required. The communication is done through a RS485 to LAN adaptor.
