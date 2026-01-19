[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-%2341BDF5.svg)](https://www.home-assistant.io)
[![Custom integration](https://img.shields.io/badge/custom%20integration-%2341BDF5.svg)](https://www.home-assistant.io/getting-started/concepts-terminology)
[![HACS](https://img.shields.io/badge/HACS-default-green.svg)](https://github.com/hacs)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/Tom-Bom-badil/home-assistant_helios-vallox/graphs/commit-activity)
[![HA Analytics](https://img.shields.io/badge/dynamic/json?url=https://analytics.home-assistant.io/custom_integrations.json&query=$.helios_vallox_ventilation.total&label=HA%20Analytics%20%2A&suffix=%20active%20installations&color=gold)](https://analytics.home-assistant.io/)

## 📝 Helios Pro / Vallox SE ventilation control (older RS485 models)

👉 This is the `Home Assistant` adaptation of my `SmartHomeNG Helios Plugin`, which has been running 24/7 since 2014 on my [previous home automation system](https://github.com/Tom-Bom-badil/helios/wiki). The plugin used to be the very first “unofficial” community-made software for these ventilation models. Over the years, it became the basis for many other system adaptations. As I switched to Home Assistant a while ago, it was a logical step to migrate the plugin to a HA custom integration.

<img width=100% alt="image1" src="https://github.com/user-attachments/assets/d8b97a5a-9df6-4e28-9e1a-657fe4616ce9" />

<br/>👉 Main features of the integration are:
- more than 30 predefined entities (common ventilation variables and settings),
- users can add their own variables without programming skills (e.g. to add custom CO₂ or humidity readings),
- polling of all known variables and settings at adjustable intervals (default: 60 s),
- writing to _ANY_ writable register, safeguarded by plausibility and validity checks before the actual write,
- many additional calculations: air throughput, power consumption, efficiency, temperature balance, etc.,
- optional calculation of the specific air throughput volumes of your house according to DIN requirements,
- full copy/paste code of an example dashboard is available on the Wiki (see screenshot),
- the dashboard also implements a mobile-friendly, software-based remote control in multiple languages: on/off, heat recovery status, fan speed, timed boost / fireplace mode - everything your wall-mounted hardware remote can do (and more!).<br/>This is particularly useful if your main display or the entire remote control is broken (over the years, I have come across quite a few).

The integration has been tested with various RS485 LAN/Wi-Fi adapters - no soldering, no additional voltage or step-down boards required. Simply use the screw / plug-in terminals of the tested adapters. Some do not even require external power, as they can run directly on bus power (see [here](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/wiki/Appendix-1-%E2%80%90-Tested-adaptors)).

## 📝 Compatible ventilation devices

If your ventilation system has this remote control board, it is almost certainly compatible:<br/>

![image](https://github.com/user-attachments/assets/9e7d9699-751b-4856-8c68-797182ef8303)

👉 Users have reported successful installations for the following models:<br/>
_`Helios EC 200 Pro R/L`, `Helios EC 300 Pro R/L`, `Helios EC 500 Pro`, `Vallox 080 SE`, `Vallox 090 SE`, `Vallox 910 SE`, `Vallox Digit SE`, `Vallo Plus 350 SE`, `Vallo Plus 510 SE`, `Vallox 130D`<br/>(the latter requires changing a few register numbers due to different addresses; see [old wiki](https://github.com/Tom-Bom-badil/SmartHomeNG-Helios/wiki))_

👉 According to manuals I came across over the years, the following models also seem to use the same proprietary Helios/Vallox protocol:<br/>
_`Vallox 096 SE`, `Vallox 110 SE`, `Vallox 121 SE` (both versions with and without front heating module), `Vallox 150 SE`, `Vallox 270 SE`, `Vallox Digit SE 2`, `Vallox ValloPlus SE 500`.<br/>(Please report back if you got the integration running on one of these models, thanks in advance!)_

## ⚙️ Installation

Installation can be done either through HACS (recommended) or manually. Please check [this Wiki page](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/wiki/Installation-and-setup) for detailed installation and configuration options.

## 📝 Notes & Feedback

👉 This integration was developed, tested, and is operated using a Helios EC300 Pro R with a USR DR134 adapter.<br/>
👉 Lots of in-depth insights into how everything works, including descriptions of RS485 fundamentals and the protocol in use, installation instructions, RS485 adapter setup / configuration / tests, and a brief project history are available [on the Wiki](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/wiki).

**Contributions welcome!**

💬 Start a [discussion](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/discussions) if you run into issues.<br/>
✅ If it works for you, please let us know - it's great to hear success stories.<br/>
📬 Pull requests, improvements and feedback in general (including newly tested adapters) are always appreciated!

_Thank you  for using this integration, and for your feedback! 😊_

---

<sub>* Active installations: Analytics numbers are based on HA Analytics opt-in users, estimated to represent less than ¼ of all active HA installations. Click the badge for more info.</sub>
