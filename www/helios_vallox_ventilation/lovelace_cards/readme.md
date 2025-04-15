
EXPERIMENTAL FEATURES!!!!


This directory contains various Lovelace cards for the ventilation.

## Remote control card

In [remote_control.yaml](./remote_control.yaml) you can find a simulated remote control. I have successfully tested it in a 1/4 screen column of a `sections`dashboard both on my PC (WQHD) and on my mobile phone; although I am still struggeling a bit with the HA companion app (iOS).

https://github.com/user-attachments/assets/61a7da07-2e30-4184-b3d3-079c99e9cbc1

To install it, you will need to create a new manual / user-defined card on your dashboard and paste the YAML into it. Both cardmod and the custom:button-card are requirements for it.

Please note: Only the remote control (the top item) is in the yaml; the 2 cards below are still work-in-progress.

## Air exchange gauge

[This gauge](gauge_air_exchange.yaml) displays the current air exchange. It requires the optional features in `user_conf.yaml` to be enabled and filled out properly. Also, you might need to adjust the yaml to you individual device.

![image](https://github.com/user-attachments/assets/f110379d-4c1f-4d32-a07b-e31d3fc4ac4f)

