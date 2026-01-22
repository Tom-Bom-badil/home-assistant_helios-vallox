[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-%2341BDF5.svg)](https://www.home-assistant.io)
[![Custom integration](https://img.shields.io/badge/custom%20integration-%2341BDF5.svg)](https://www.home-assistant.io/getting-started/concepts-terminology)
[![HACS](https://img.shields.io/badge/HACS-default-green.svg)](https://github.com/hacs)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/Tom-Bom-badil/home-assistant_helios-vallox/graphs/commit-activity)
[![HA Analytics](https://img.shields.io/badge/dynamic/json?url=https://analytics.home-assistant.io/custom_integrations.json&query=$.helios_vallox_ventilation.total&label=HA%20Analytics%20%2A&suffix=%20active%20installations&color=gold)](https://analytics.home-assistant.io/)

## 📝 Helios Pro / Vallox SE ventilation control (for older RS485 models)

👉 This is the Home-Assistant adaptation of my _SmartHomeNG Helios Plugin_, which<br/>
has been running 24/7 since 2014 on my previous home automation system. That plugin<br/>
used to be the first community-made software for these ventilation models. Over the<br/>
years, it became the basis for many other system adaptations.<br/>
<br/>
As I migrated to HA a while ago, I reworked the plugin to be a HA custom integration.

<img width=60% alt="pic2" src="https://github.com/user-attachments/assets/73d53c99-5a01-43ab-8190-f305bbff503c" />

<br/>👉 Main features of the integration are:

- 70+ predefined entities for common ventilation registers and derived values
- user-defined entities without programming (e.g. for CO₂ or humidity sensors)
- configurable polling interval for all registers (default: 60 s)
- write access to any writable register with plausibility and validity checks
- extensive derived calculations (airflow, power, efficiency, temperature balance)
- DIN-based calculation of the required 'design' airflow (individual to your house)
- ready-to-use example dashboard, available for copy/paste in the Wiki
- mobile-friendly, multi-language software remote replacing the wall-mounted controller

The software-based remote control is especially useful if your remote control display<br/>
became unreadable, or the wall-mounted remote itself is broken or no longer available.

The integration has been tested with various RS485 LAN/Wi-Fi adapters.<br/>
No soldering, no additional voltage or step-down boards required.<br/>
Simply use the screw / plug-in terminals of the tested adapters.<br/>
Some do not even require external power, they just run on bus power (see [here](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/wiki/Appendix-1-%E2%80%90-Tested-adaptors)).

## 📝 Compatible ventilation devices

If your ventilation system has this remote control, it is almost certainly compatible:<br/>

![image](https://github.com/user-attachments/assets/9e7d9699-751b-4856-8c68-797182ef8303)

👉 Over the years, users have reported the successful installation for:<br/>
_`Helios EC 200 Pro`, `Helios EC 300 Pro`, `Helios EC 500 Pro`, `Vallox 130D`,<br/>
`Vallox 080SE`, `Vallox 090SE`, `Vallox 096SE`, `Vallox 121SE`, `Vallox 145SE`,<br/>
 `Vallox 910SE`, `Vallox Digit SE`, `Vallo Plus 350SE`, `Vallo Plus 510SE`<br/>
(the 130D requires changing a few register numbers due to different addresses; see [old wiki](https://github.com/Tom-Bom-badil/SmartHomeNG-Helios/wiki))._

👉 According to docs I came across, the following models should also work:<br/>
_`Vallox 110SE / 150 SE / 270SE`, `Vallox Digit SE2`, `Vallox ValloPlus 500SE`.<br/>
(Please report back if you got it working on one of these models, thanks in advance!)_

## ⚙️ Installation

Installation can be done either through HACS (recommended) or manually.<br/>
Please check [this Wiki page](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/wiki/Installation-and-setup) for installation and configuration.

## 📝 Notes and feedback

👉 Lots of in-depth insights into how everything works, including descriptions of RS485<br/>
fundamentals and the protocol in use, installation instructions, RS485 adapter configuration<br/>
and tests, and a brief project history are available [on the Wiki](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/wiki).<br/>
<br/>
The Wiki also contains a 'Tinkerers corner' section with useful hardware and repair information.

**Contributions welcome!**

💬 Start a [discussion](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/discussions) if you run into issues.<br/>
✅ If it works for you, please let us know - it's great to hear success stories.<br/>
📬 Pull requests, improvements and feedback in general are always appreciated!

_Thank you for using this integration, and for your feedback! 😊_

---

<sub>* Active installations: Analytics numbers are based on HA Analytics opt-in users,<br/>
estimated to represent less than ¼ of all active HA installations. Click the badge for more info.</sub>
