
EXPERIMENTAL FEATURES!!!!


This directory contains various Lovelace cards for the ventilation. Some are still under developemnt.

## Remote control

In [remote_control.yaml](./remote_control.yaml) you can find a simulated remote control. I have successfully tested it in a 1/4 screen column of a `sections`dashboard both on my PC (WQHD) and on my mobile phone; although I am still struggeling a bit with the HA companion app (iOS).

https://github.com/user-attachments/assets/61a7da07-2e30-4184-b3d3-079c99e9cbc1

To install it, you will need to create a new manual / user-defined card on your dashboard and paste the YAML into it. Both cardmod and the custom:button-card are requirements for it.

Please note: Only the remote control (the top item) is in the yaml; the 2 cards below are still work-in-progress.

## Fanspeed control (work in progress!!!)

![image](https://github.com/user-attachments/assets/13dda314-775c-4e32-934c-2b3ac26ab0c6)

## Air exchange gauge

[This gauge](gauge_air_exchange.yaml) displays the current air exchange. It requires the optional features in `user_conf.yaml` to be enabled and filled out properly. Also, you might need to adjust the yaml to you individual device.

![image](https://github.com/user-attachments/assets/f110379d-4c1f-4d32-a07b-e31d3fc4ac4f)

## Fanspeed gauge

![image](https://github.com/user-attachments/assets/93cf19d1-6151-4809-b7d9-d2f59b6d3e4a)

## Electrical power gauge

![image](https://github.com/user-attachments/assets/c4cde6cc-f039-4408-a653-ac4bca79c1af)

## Efficiency gauge

![image](https://github.com/user-attachments/assets/622e1104-7b20-4011-871f-ada109c4a7e8)

## Temperatures with airflow

![image](https://github.com/user-attachments/assets/b8dbbcfe-0a4d-404e-a590-d21288d64d3c)

## Table with calculated airflow requirements

![image](https://github.com/user-attachments/assets/1415aed6-fd67-46be-840b-1f51dede7a24)


