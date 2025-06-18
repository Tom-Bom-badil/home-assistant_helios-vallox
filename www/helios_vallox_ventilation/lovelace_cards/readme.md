
Requires version 2025.06.01+
SOME FEATURES ARE STILL EXPERIMENTAL!!!!

# Custom ventilation cards

I am currently working on various custom cards. Some are just for fun (like gauges), but some implement a full replcaement for your remote control (over the years, I have been in contact with quite some people with a defect remote control board and/or broken display). The cards can be found in the [lovelace_cards directory](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/tree/develop/www/helios_vallox_ventilation/lovelace_cards).

Important: Read the installation instructions carefully; some cards have special requirements or dependencies.
I am a big fan of a minimizing the number of the add-ons in my production HA, but some just cannot be avoided.

## Interactive remote control #1 (e.g. for use on smartphones)

In [remote_control.yaml](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/blob/develop/www/helios_vallox_ventilation/lovelace_cards/card_remote_control.yaml) you can find a simulated remote control. All buttons are fully functional - they are working like in the physical remote control at your wall. The card has been tested both in a 1/4 screen column of a `sections`dashboard on a PC (WQHD), and in the companion app on my cell phone.

![remote_control](https://github.com/user-attachments/assets/a2e4e568-ec17-4686-b9fe-4b24ae258e64) &nbsp;&nbsp;&nbsp;&nbsp; ![ha_companion_app](https://github.com/user-attachments/assets/66f70478-2dfc-4228-b406-33959417aed3)

Installation:
- make sure you have cardmod and button-card installed (e.g. through HACS),
- also make sure that you copied the following files into <ha_root>/www/helios_vallox_ventilation: [remote_control.png](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/blob/develop/www/helios_vallox_ventilation/remote_control.png) (background pic), [LED_on.png](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/blob/develop/www/helios_vallox_ventilation/LED_on.png) (green indicator light), [LED_off.png](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/blob/develop/www/helios_vallox_ventilation/LED_off.png) (grey indicator light)
- optional: create a new page on your dashboard; ideally it should contain a column of 1/4...1/3 page width (if you plan using the card on a PC's display)
- create a new card (of 'manual' type), copy/paste [the code](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/blob/develop/www/helios_vallox_ventilation/lovelace_cards/card_remote_control.yaml) into the YAML of that new card
- save and enjoy :)

_ToDo / note to self: In certain screen resolutions, the light green display background has some odd formatting (so it still needs some proper / different positioning)._

## Interactive remote control #2 (e.g. for use on smartphones)

The [fanspeed card](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/blob/develop/www/helios_vallox_ventilation/lovelace_cards/card_fanspeed.yaml) is for (quick-)switching the ventilation level, and also implements an easy-to-use boost air control. If you put it underneath your normal remote control (see above), you can have the full control of your ventilation device incl. boost air on your mobile phone.

![fanspeed](https://github.com/user-attachments/assets/325a263c-6991-405b-83b8-10d90ade01e1)&nbsp;&nbsp;&nbsp;&nbsp;![boost_air](https://github.com/user-attachments/assets/6e1a404b-653f-4bee-adf7-45bff8e1c06a)

Installation
- _Note: This is a 2-step installation as we are using macros for the buttons - this will save us almost 300 lines of redundant code for the 8 buttons!_
- make sure you have cardmod and button-card installed (e.g. through HACS),
- go to your dashboard and the page you want to insert the card, click the 3 dots on the outermost top right, choose YAML editing (important - we are not editing the PAGE, but the DASHBOARD!!!)
- line 1 is your dashboard name - this needs to be kept; click to the end of line 1 and press <Enter> for a new, empty line 2
- copy/paste the code of [button_card_templates.yaml](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/blob/develop/www/helios_vallox_ventilation/lovelace_cards/button_card_templates.yaml) here; your code should look as follows: ![image](https://github.com/user-attachments/assets/2bc103f2-97cc-4b83-9278-b378b714571a)
- create a new card (of 'manual' type), copy/paste [the code](https://github.com/Tom-Bom-badil/home-assistant_helios-vallox/blob/develop/www/helios_vallox_ventilation/lovelace_cards/card_fanspeed.yaml) into the YAML of that new card
- save and enjoy :).

## Gauges

### Air exchange
[This gauge](gauge_air_exchange.yaml) displays the current air exchange:<br/><br/>
![image](https://github.com/user-attachments/assets/f110379d-4c1f-4d32-a07b-e31d3fc4ac4f)

Requirements:
- integration up and running
- correct values in house_area and isolation_factor in `secrets.yaml` for volume calculations
- correct values in airflow_per_mode and max_airflow in `secrets.yaml` for gauge and needle

Background:<br/><br/>
German DIN norm 1946-6 defines the general requirements for a house ventilation concept, which includes the formulas for the calculation of 4 different ventilation levels: Ventilation for moisture protection, reduced ventilation, nominal (standard) ventilation and intensive ventilation (boost mode). Such a ventilation concept is mandatory for dimensioning the ventilation in the design / planning phase of a building. As each building is different, the formulas consider living area as well as the general quality of the house isolation.

Modification / adjustment to different ventilation models<br/><br/>
The numbers used in the gauge are for a Helios EC 300 Pro. I have been desparetly searching for a HA gauge with proper gradients, but didn't find any, so I had to build something by hand. The following tool is very useful if you want to adjust the colors in the `segments:` section to a different model: [https://ha.labtool.pl/en.lims](https://ha.labtool.pl/en.lims?e=JmZjQ1M2EiLCJmZWQ3MDkiLCI0NGEwNDciLCJmZWQ3MDkiLCJmNzg2M2IiLCJmZjAwMDAiXSwic3RlcHMiOlsxMCwxMCwxMCwxMCwxMF0sInJhbmdlIjpbIjAiLCI0OSIsIjExNCIsIjE2NCIsIjE4OCIsIjM2MCJdfQ)

Additional remarks:<br/><br/>
Please consider the displayed value of the current air exchange as a 'guidance'. The current condition of your filters as well as the pressure loss due to bendings in your duct system prevent a precise displaying of your current airflow. However, this gauge is a nice general indication for the air volumes in the different fan speeds.
