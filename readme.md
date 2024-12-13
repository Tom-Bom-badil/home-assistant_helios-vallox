# Home Assistant: Integration for Helios / Vallox devices with RS485 Modbus (pre-EasyControls / pre-2014 models)

This is the HA-adaption of my Python script that used to work in my previous home automation system for >10 years (see [here](https://github.com/Tom-Bom-badil/helios/wiki), also for Wiki/docs/how-to's - it will take a bit until I moved everything over here). Users have confirmed that the following models are compatible to the protocol implemented in this custom component:

- Helios EC 200 Pro R/L
- Helios EC 200 Pro R/L
- Vallo Plus 510 SE
- Vallo Plus 350SE
- Vallox 910SE
- Vallox 090 SE
- Vallox Digit SE
- Vallox 130D (not all registers reported working or with same number, see see wiki)

The protocol we are utilizing for reading and writing is Modbus-like; however, it is not exactly Modbus, so an individual implementation is required (pyModbus simply doesn't work for this).

The HA implementation is now socket-based and doesn't need anymore serial tools like socat, netcat etc for communicating with a RS485-LAN/Wifi adaptor.

Please note: This software is still under development - we hit the end of the Alpha phase and it is working well for me, so I made it available to the public.
