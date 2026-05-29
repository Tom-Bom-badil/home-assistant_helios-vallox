# Helios Pro / Vallox SE ventilation control<br/><sup><sub>(for models with  built-in RS485 and Modbus-like Protocol)</sub></sup>


[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-%2341BDF5.svg)](https://www.home-assistant.io)
[![Custom integration](https://img.shields.io/badge/Custom%20Integration-%2341BDF5.svg)](https://www.home-assistant.io/getting-started/concepts-terminology)
[![HACS Listing](https://img.shields.io/badge/HACS%20Listing-default-green.svg)](https://github.com/hacs)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/Tom-Bom-badil/home-assistant_helios-vallox/graphs/commit-activity)
[![HA Analytics](https://img.shields.io/badge/dynamic/json?url=https://analytics.home-assistant.io/custom_integrations.json&query=$.helios_vallox_ventilation.total&label=HA%20Analytics&suffix=%20installations%20%2A&color=green)](https://analytics.home-assistant.io/)

<sup><sub>* It is estimated that less than ¼ of all HA users have opted in to HA Analytics to share their usage data, so the actual number of installations is likely way higher.</sub></sup>

---

## Overview

👉 This is the Home-Assistant adaptation of my _SmartHomeNG Helios Plugin_, which<br/>
has been running 24/7 since 2014 on my previous home automation system. That plugin<br/>
used to be the first community-made software for these ventilation models. Over the<br/>
years, it became the basis for many other system adaptations.<br/>
<br/>
As I migrated to HA a while ago, I reworked the plugin to be a HA custom integration:

<a href="https://raw.githubusercontent.com/wiki/Tom-Bom-badil/home-assistant_helios-vallox/images/dashboard.png">
  <img width=70% alt="img1" src="https://raw.githubusercontent.com/wiki/Tom-Bom-badil/home-assistant_helios-vallox/images/dashboard.png" />
</a>

👉 Main features of the integration are:

- 50+ predefined entities for common ventilation registers and derived values
- write access to any writable register with plausibility and validity checks
- a callable write service for your automations and helpers
- extensive derived calculations (airflow, power, efficiency, temperature balance)
- DIN-based calculation of the required 'design' airflow (individual to your house)
- ready-to-use example dashboard, available for copy/paste in the Wiki
- mobile-friendly, multi-language software remote replacing the hardware remote

The software-based remote control is especially useful when your wall-mounted remote<br/>control display became unreadable, or the remote itself is broken or no longer available.<br/>You can simply use your Smartphone to control the ventilation - including a new, much<br/>simplified 'software boost mode':

<a href="https://raw.githubusercontent.com/wiki/Tom-Bom-badil/home-assistant_helios-vallox/images/mobile-dashboard.png">
  <img width=70% alt="img1" src="https://raw.githubusercontent.com/wiki/Tom-Bom-badil/home-assistant_helios-vallox/images/mobile-dashboard.png" />
</a>

The integration has been tested with various RS485 LAN/Wi-Fi adapters.<br/>
For most of them, no soldering, no additional voltage or step-down boards are required.<br/>
Simply use the screw / plug-in terminals of the tested adapters (see [here](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/wiki/Appendix-1-%E2%80%90-Tested-adaptors)).<br/>
Some adapters do not even require external power, they are just running on bus power.

## 📝 Compatible ventilation devices

If your ventilation system has this remote control, it is almost certainly compatible:<br/>

![image](https://github.com/user-attachments/assets/9e7d9699-751b-4856-8c68-797182ef8303)

👉 Over the years, users have reported the successful installation for:<br/>
_`Helios EC 200/300/500 Pro`, `Vallox Digit SE`, `Vallox 130 D`,<br/>
`Vallox 080/090/096/121/145/150 SE`, `ValloPlus 350/500/510/910 SE`._<br/>
_(the 130D requires changing a few register numbers due to different addresses; see [old wiki](https://github.com/Tom-Bom-badil/SmartHomeNG-Helios/wiki))._

👉 According to docs I came across, the following models should also work:<br/>
_`Vallox 110/150/270 SE`, `Vallox Digit SE2`.<br/>
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
