# gpx-radiation-tracker
This two little script which reads CPR from a GMC-500 geiger counter and gps data from a gps *(VK-162 G-Mouse Remote Mount USB GPS)* device to create gpx tracks or influx time series

- GMC-500: https://www.gqelectronicsllc.com/comersus/store/comersus_viewItem.asp?idProduct=5631

# Usage: gpx-radiation-tracker

```
./gpx-radiation-tracker > default.gpx
```
The runtime information is written to STDERR.

# Usage: influx-radiation-tracker

```
./influx-radiation-tracker 
```
For this you need to setup gafana and add a dashboard from **./Grafana Dashboards**


# Screenshots

![Screenshot_0](:/Screenshots/Screenshot_0.png?raw=true "Simulation of a nuclear meltdown")
![Screenshot_1](:/Screenshots/Screenshot_1.png?raw=true "Default view updated every 5s")
![Screenshot_2](./Screenshots/Screenshot_2.png?raw=true "Track view")


