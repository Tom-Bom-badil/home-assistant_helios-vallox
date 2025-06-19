[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-%2341BDF5.svg)](https://www.home-assistant.io)
[![Custom integration](https://img.shields.io/badge/custom%20integration-%2341BDF5.svg)](https://www.home-assistant.io/getting-started/concepts-terminology)
[![HACS](https://img.shields.io/badge/HACS-default-green.svg)](https://github.com/hacs)
[![Version](https://img.shields.io/badge/Version-v2025.06.1-green.svg)](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/releases)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/Tom-Bom-badil/home-assistant_helios-vallox/graphs/commit-activity)

## HA Integration for Helios Pro / Vallox SE ventilation systems (pre-EasyControls / pre-2014 models with RS-485)

This is the Home Assistant adaptation of my Python script, which has been running 24/7 in my previous home automation system since 2014 (see [here](https://github.com/Tom-Bom-badil/helios/wiki)). In-depth insights, how-to's, installation instructions,  adapter setup / configuration and a brief project history of the last 10 years of programming are documented in detail [on the Wiki](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/wiki).

By default, the integration reads more than 30 common variables from the ventilation unit at regular intervals (60s, adjustable). You can optionally add further variables which my own ventilation doesn't have by simply editing the configuration files (useful if you have additional humidity or CO₂ sensors) - no programming skills are required for that, just amend the integration's configuration files.

The integration also implements writing to ANY writable register in the ventilation unit, including plausibility and safety checks before the actual write. This can be used e.g. in your automations, in the Lovelace GUI on buttons / sliders / dropdowns, or directly from the developer tools:
```yaml
action: helios_vallox_ventilation.write_value
data:
  variable: fanspeed
  value: 5
```
The integration has been tested with various RS485-LAN/Wi-Fi adapters - no soldering, no additional voltage or stepdown boards etc required. Simply use the screw / plugin terminals of your LAN/Wi-Fi adapter. For specific adapters, you can even remove the external power supply and run everything from bus power (see wiki).

## Compatible devices

If your ventilation system has this remote control board, it is almost certainly compatible:<br/><br/>
![image](https://github.com/user-attachments/assets/9e7d9699-751b-4856-8c68-797182ef8303)

Users have reported the successful use on the following models:
- Helios EC 200 Pro R/L, Helios EC 300 Pro R/L, Helios EC 500 Pro R/L, Vallox 090 SE, Vallox 910 SE, Vallox Digit SE, Vallo Plus 350 SE, Vallo Plus 510 SE, Vallox 130D (this one requires changing a few register numbers due to different addresses; see [old wiki](https://github.com/Tom-Bom-badil/SmartHomeNG-Helios/wiki))

Documentations show that the following models also use the proprietary Helios/Vallox protocol, therefore they should also work:
- Vallox 096 SE, Vallox 110 SE, Vallox 121 SE (both versions with and without front heating module), Vallox 150 SE, Vallox 270 SE, Vallox Digit SE 2, Vallox ValloPlus SE 500. (Please report back if you got the integration running on one of these models, thanks in advance!)

## Installation (either through HACS or manually)

Please check [this Wiki page](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/wiki/Installation-and-setup-within-HA) for detailed installation and configuration options.

Thanks for downloading, and please leave a star and report back in the discussions section if you find this of any use for you or run into any problems - enjoy! :)

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
