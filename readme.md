[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-%2341BDF5.svg)](https://www.home-assistant.io)
[![Custom integration](https://img.shields.io/badge/custom%20integration-%2341BDF5.svg)](https://www.home-assistant.io/getting-started/concepts-terminology)
[![HACS](https://img.shields.io/badge/HACS%20listed-not_yet-red.svg)](https://github.com/hacs)
[![HACS](https://img.shields.io/badge/HACS%20install-verified-green.svg)](https://github.com/hacs)
[![Version](https://img.shields.io/badge/Version-v2025.01.1-green.svg)](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/releases)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/Tom-Bom-badil/home-assistant_helios-vallox/graphs/commit-activity)

# Integration for Helios / Vallox central house ventilation systems with RS-485 bus (pre-EasyControls aka pre-2014 models)

This is the HA adaption of my Python script that used to work in my previous home automation system for >10 years (see [here](https://github.com/Tom-Bom-badil/helios/wiki)). I am currently transferring and translating the information from there here - please check the [current Wiki](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/wiki) in this repo for more detailed information on how everything works.

Users have confirmed that the following models are compatible to the protocol implemented by this integration:

- Helios EC 200 Pro R/L
- Helios EC 300 Pro R/L
- Helios EC 500 Pro R/L
- Vallox 090 SE
- Vallox 910 SE
- Vallox Digit SE
- Vallo Plus 350 SE
- Vallo Plus 510 SE
- Vallox 130D (not all registers reported working as some have different addresses, see old wiki)

Reportedly, the following models should also work (please report back if you can confirm any of them):

- Vallox 096 SE
- Vallox 110 SE
- Vallox 121 SE (both versions with and without front heating module)
- Vallox 150 SE
- Vallox 270 SE
- Vallox Digit SE 2
- Vallox ValloPlus SE 500

The proprietary protocol on the RS-485 bus of the ventilation devices is Modbus-like. However: It is not EXACTLY Modbus. So, an individual protocol implementation is needed (pyModbus or the standard HA modbus implemetation simply don't work here).

The previous version of my main script was based on serial communication through a virtual serial port, which was doing fine for years for many users. However, in the early stages of the HA adoption, I tinkered around and found it quite hard to add the necessary standard UNIX/Linux tools like *socat* or *netcat* to HAOS (there is a way, but I would call it an `ugly hack` by utilizing ssh and command line - nothing the default end user would prefer to do). So, this HA version has been implemented with socket-based communication instead of reading/writing through virtual COM ports, resulting in a direct network connection between the integration and the RS485-LAN/Wifi adaptor (no additional tools needed).

## What does this Integration do?

The integration creates a bunch of sensors, binary_sensors and switches to control your ventilation. All those entities are prefixed with `ventilation_`, so you can easily filter all of them at once in the developer tools.

Also, the integration will install a writing service for use in your automations:
```yaml
action: helios_vallox_ventilation.write_value
data:
  variable: "fanspeed" # entity name after the "ventilation_" prefix
  value: 1             # the value
```

If you want to test the write service by hand in the developer tools: Choose `Helios Pro / Vallox SE Ventilation: write_value` and copy/paste the yaml above into the text field.

Please note that most registers and coils are read-only, and many have only a few valid values. The integration will take care of that - so better look up it's attributes in the developer tools before writing to an entity, I have included all valid options as far as known to me or stated in the manuals / docs.

## Installation through HACS

*Pro tip: Please do not restart until finished. Finished means 'finished finished'.*

Launch HACS and click the 3 dots top right corner, then choose `Custom repositories`.

You will see 2 fields you have to fill out:

- Repository: **https://github.com/Tom-Bom-badil/home-assistant_helios-vallox**
- Type: **Integration**

Click add, download it and read the pro tip above again - do not restart yet in order to avoid another restart lateron.

Add this to your secrets.yaml (adjust IP and Port of your LAN/Wifi-RS485 adaptor as needed):
```yaml
helios_vallox_ip:   192.168.178.38
helios_vallox_port: 8234
```

Add this to your configuration.yaml:
```yaml
helios_vallox_ventilation:
  !include custom_components/helios_vallox_ventilation/vent_conf.yaml
```

Optionally: If you want to have detailed debug logs at the beginning, you can also add this to your configuration.yaml:
```yaml
logger:
  logs:
    custom_components.helios_vallox_ventilation: error
```

This is the point where you are 'finished finished' - you can now restart HA once and enjoy the integration!

## Manual installation

Upload the directories and files with original pathes to your HA.

Then add this to your secrets.yaml (adjust IP and Port of your LAN/Wifi-RS485 adaptor as needed):
```yaml
helios_vallox_ip:   192.168.178.38
helios_vallox_port: 8234
```

Add this to your configuration.yaml:
```yaml
helios_vallox_ventilation:
  !include custom_components/helios_vallox_ventilation/vent_conf.yaml
```

Optionally: If you want to have detailed debug logs at the beginning, you can also add this to your configuration.yaml:
```yaml
logger:
  logs:
    custom_components.helios_vallox_ventilation: error
```

Finally restart HA and enjoy! :)

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
