[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-%2341BDF5.svg)](https://www.home-assistant.io)
[![Custom integration](https://img.shields.io/badge/custom%20integration-%2341BDF5.svg)](https://www.home-assistant.io/getting-started/concepts-terminology)
[![HACS](https://img.shields.io/badge/HACS%20listing-applied-red.svg)](https://github.com/hacs)
[![HACS](https://img.shields.io/badge/HACS%20install-verified-green.svg)](https://github.com/hacs)
[![Version](https://img.shields.io/badge/Version-v2025.03.1-green.svg)](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/releases)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/Tom-Bom-badil/home-assistant_helios-vallox/graphs/commit-activity)

## HA Integration for Helios Pro / Vallox SE ventilation systems (pre-EasyControls / pre-2014 models with RS-485)

This is the Home Assistant adaptation of my Python script, which has been running 24/7 in my previous home automation system since 2014 (see [here](https://github.com/Tom-Bom-badil/helios/wiki)).

By default, the integration reads more than 30 common variables from the ventilation unit at regular intervals. It can be extended to include additional variables (e.g., for individual humidity or CO₂ sensor setups) by simply editing the configuration files - no programming is required.

The integration also implements a writing service, which can be used for ANY writable register of the ventilation system, including plausibility checks for register IDs and values before the actual write:
```yaml
action: helios_vallox_ventilation.write_value
data:
  variable: fanspeed
  value: 5
```

The integration has been tested with various RS485-LAN/Wi-Fi adapters - no soldering, no additional voltage / stepdown boards etc required. Simply use the screw terminals or plugin ports of your LAN/Wi-Fi adapter for the wires. For specific adapters, you can even remove the external power supply and use bus power.

In-depth insights, how-to's, installation instructions and adapter setup/configuration can be checked out [here in the detailed Wiki](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/wiki).

## Compatible devices

If your ventilation system has this remote control board, it is almost certainly compatible:<br/><br/>
![fb1_small](https://github.com/user-attachments/assets/57bbe02d-9086-4028-849f-c43d699e2aed)

Users have reported the successful use on the following models:
- Helios EC 200 Pro R/L, Helios EC 300 Pro R/L, Helios EC 500 Pro R/L, Vallox 090 SE, Vallox 910 SE, Vallox Digit SE, Vallo Plus 350 SE, Vallo Plus 510 SE, Vallox 130D (this one requires changing a few register numbers due to different addresses; see [old wiki](https://github.com/Tom-Bom-badil/SmartHomeNG-Helios/wiki))

Documentations show that the following models also use the proprietary Helios/Vallox protocol, therefore they should also work:
- Vallox 096 SE, Vallox 110 SE, Vallox 121 SE (both versions with and without front heating module), Vallox 150 SE, Vallox 270 SE, Vallox Digit SE 2, Vallox ValloPlus SE 500. (Please report back if you got the integration running on one of these models, thanks in advance!)

## Installation through HACS

Launch HACS and click the 3 dots in the top right corner, then choose `Custom repositories`. You will see 2 fields to fill out:

- Repository: _**https://github.com/Tom-Bom-badil/home-assistant_helios-vallox**_
- Type: _**Integration**_

Click add and download the integration. Do NOT restart yet to avoid restarting twice.

Add this to your `secrets.yaml` file in the HA root (adjust the IP and port of your LAN/Wifi-RS485 adaptor as needed):
```yaml
helios_vallox_ip:   192.168.178.38
helios_vallox_port: 502
```

Now add this to your `configuration.yaml` to set up the integration and its log level:
```yaml
logger:
  logs:
    helios_vallox: error      # set to 'info' or even 'debug' for more details

helios_vallox_ventilation:
  !include custom_components/helios_vallox_ventilation/vent_conf.yaml
```
Restart HA to load the integration, and enjoy! :)

## Manual installation

Upload the directories and files with original pathes to your HA.

Add this to your `secrets.yaml` file in the HA root (adjust the IP and port of your LAN/Wifi-RS485 adaptor as needed):
```yaml
helios_vallox_ip:   192.168.178.38
helios_vallox_port: 8234
```

Now add this to your `configuration.yaml` to set up the integration and its log level:
```yaml
logger:
  logs:
    helios_vallox: error      # set to 'info' or even 'debug' for more details

helios_vallox_ventilation:
  !include custom_components/helios_vallox_ventilation/vent_conf.yaml
```

Restart HA to load the integration, and enjoy! :)

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
