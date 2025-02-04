[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-%2341BDF5.svg)](https://www.home-assistant.io)
[![Custom integration](https://img.shields.io/badge/custom%20integration-%2341BDF5.svg)](https://www.home-assistant.io/getting-started/concepts-terminology)
[![HACS](https://img.shields.io/badge/HACS%20listing-applied-red.svg)](https://github.com/hacs)
[![HACS](https://img.shields.io/badge/HACS%20install-verified-green.svg)](https://github.com/hacs)
[![Version](https://img.shields.io/badge/Version-v2025.01.3-green.svg)](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/releases)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/Tom-Bom-badil/home-assistant_helios-vallox/graphs/commit-activity)

## HA Integration for Helios Pro / Vallox SE ventilation systems (pre-EasyControls / pre-2014 models with RS-485)

This is the Home Assistant adaption of my Python script that used to work 24/7 in my previous home automation system since 2014 (see [here](https://github.com/Tom-Bom-badil/helios/wiki)).

By default, the integration reads out more than 30 common variables of the ventilation unit in regular intervals. It can be extended by further variables (e.g. for individual humidity / CO2 sensor setup) by just editing the configuration files; no programming is needed.

The integrations also implements a writing service, which can be used for ANY writeable register of the ventilation, including plausibility checks of registers id's as well as values before the actual write:
```yaml
action: helios_vallox_ventilation.write_value
data:
  variable: fanspeed
  value: 5
```

The integration has been tested with various RS485-LAN/Wifi adaptors - no soldering together of small boards required, just use the screw terminals or plugin-ports of your LAN / Wifi adaptor. For specific adaptors, you can even remove the external power supply and use the bus power. For in-depth insights, how-to's and adaptor setup / configuration, please check out the [detailed Wiki](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/wiki).

## Compatible devices

If your ventilation has this remote control board, it is almost sure that it is compatible:<br/><br/>
![fb1_small](https://github.com/user-attachments/assets/57bbe02d-9086-4028-849f-c43d699e2aed)

Users have confirmed the installation on the following models:
- Helios EC 200 Pro R/L, Helios EC 300 Pro R/L, Helios EC 500 Pro R/L, Vallox 090 SE, Vallox 910 SE, Vallox Digit SE, Vallo Plus 350 SE, Vallo Plus 510 SE, Vallox 130D (this one requires changing a few register numbers due to different addresses, see [old wiki](https://github.com/Tom-Bom-badil/SmartHomeNG-Helios/wiki))

Reportedly, the following models are also using the propriety Helios/Vallox protocol:
- Vallox 096 SE, Vallox 110 SE, Vallox 121 SE (both versions with and without front heating module), Vallox 150 SE, Vallox 270 SE, Vallox Digit SE 2, Vallox ValloPlus SE 500.


## Installation through HACS

Launch HACS and click the 3 dots top right corner, then choose `Custom repositories`. You will see 2 fields you have to fill out:

- Repository: _**https://github.com/Tom-Bom-badil/home-assistant_helios-vallox**_
- Type: _**Integration**_

Click add and download it. Do not restart yet in order to avoid another restart lateron.

Add this to the `secrets.yaml` file in your HA root (adjust IP and Port of your LAN/Wifi-RS485 adaptor as needed):
```yaml
helios_vallox_ip:   192.168.178.38
helios_vallox_port: 8234
```

Now add this to your `configuration.yaml` to setup the integration and its log level:
```yaml
logger:
  logs:
    custom_components.helios_vallox_ventilation: error

helios_vallox_ventilation:
  !include custom_components/helios_vallox_ventilation/vent_conf.yaml
```
Restart HA for loading the integration, and enjoy! :)

## Manual installation

Upload the directories and files with original pathes to your HA.

Add this to the `secrets.yaml` file in your HA root (adjust IP and Port of your LAN/Wifi-RS485 adaptor as needed):
```yaml
helios_vallox_ip:   192.168.178.38
helios_vallox_port: 8234
```

Now add this to your `configuration.yaml` to setup the integration and its log level:
```yaml
logger:
  logs:
    custom_components.helios_vallox_ventilation: error

helios_vallox_ventilation:
  !include custom_components/helios_vallox_ventilation/vent_conf.yaml
```

Restart HA for loading the integration, and enjoy! :)

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
