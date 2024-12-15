## Home Assistant: Integration for Helios / Vallox devices with RS485 Ports (pre-EasyControls aka pre-2014 models)

> **This software is still under development - we hit the end of the Alpha phase, and it is working well for me, so I made it available to the public. Lot's of features are yet to come, including a graphical configuration (although it's only IP and Port that need to be configured). Also, a default lovelace card will be part of this project. Working on this right now.**

This is the HA-adaption of my Python script that used to work in my previous home automation system for >10 years (see [here](https://github.com/Tom-Bom-badil/helios/wiki), also for Wiki/docs/how-to's - it will take a bit until I moved everything over here). Users have confirmed that the following models are compatible to the proprietary protocol implemented in this custom component:

- Helios EC 200 Pro R/L
- Helios EC 300 Pro R/L
- Helios EC 500 Pro R/L
- Vallo Plus 510 SE
- Vallo Plus 350SE
- Vallox 910SE
- Vallox 090 SE
- Vallox Digit SE
- Vallox 130D (not all registers reported working or with same number, see see wiki)

The protocol we are utilizing for reading and writing is Modbus-like; however, it is not exactly Modbus, so an individual implementation is required (pyModbus or the standard HA modbus implemetation simply don't work for this).

The HA implementation is now socket-based and doesn't need anymore serial tools like socat, netcat etc for communicating with a RS485-LAN/Wifi adaptor.

### Installation

Upload the directories and files with original pathes to your HA.

Then add this to your secrets.yaml (adjust IP and Port of your LAN/Wifi-RS485 adaptor as needed):
```yaml
helios_vallox_ip:   192.168.178.38
helios_vallox_port: 8234
```

Add this to your configuration.yaml:
```yaml
helios_vallox_ventilation:  !include custom_components/helios_vallox_ventilation/configuration.yaml
```

Optionally: If you want to have detailed debug logs at the beginning, you can also add this to your configuration.yaml:
```yaml
logger:
  logs:
    custom_components.helios_vallox_ventilation: debug
```

Finally restart HA and enjoy! :)
