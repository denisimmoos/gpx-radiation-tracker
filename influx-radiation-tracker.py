#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import serial
import signal
import sys
from time import sleep
from datetime import datetime, timezone
import math

from influxdb import InfluxDBClient

influxdb_name = "gpscpm"
influxdb_retention = "2m"

influxdb = InfluxDBClient(host='localhost', port=8086)
# influxdb.drop_database(influxdb_name)
influxdb.create_database(influxdb_name)
influxdb.switch_database(influxdb_name)
influxdb.create_retention_policy(
    name=influxdb_name,
    duration=influxdb_retention,
    replication=1,
    database=influxdb_name,
    default=False)


# gps settings
gps_port = "/dev/ttyACM0"
gps_baudrate = 9600
gps_timeout = 0

# geiger settings
geiger_port = '/dev/ttyUSB0'
geiger_baudrate = 115200

# initialize serial connections
gps_ser = serial.Serial(
    port=gps_port,
    baudrate=gps_baudrate,
    timeout=gps_timeout)

geiger_ser = serial.Serial(
    port=geiger_port,
    baudrate=geiger_baudrate)

# some counters
gpgga_initial = []
cpm_array = []
gpgga = []

# SIG handles
def handler(signum, frame):
    eprint("Ctrl-c was pressed. Do you really want to exit? y/n ")
    res = input()
    if res == 'y':
        exit(1)

# initialize signal handler
signal.signal(signal.SIGINT, handler)


# print to stderr
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


# avg of a list
def listavg(lst):
    return sum(lst) / len(lst)

def getCPM(ser):

    cpm = 0
    counter = 0
    maxcount = 2

    while cpm == 0:
        ser.write(b'<GETCPM>>')
        srec = ser.read(2)
        rec = chr(srec[0]) + chr(srec[1])
        cpm = int(ord(rec[0]) << 8 | ord(rec[1]))
        counter += 1
        # this will prevent it to run amok
        if counter > maxcount:
            return 0

    return cpm

def gpsGPGGA(data):

    """parse the $GPGGA string from GPS device"""

    # get GPS info
    if "$GPGGA" in data:
        s = data.split(",")

        if s[6] == "0":
            # no gps data
            return 0
        else:

            # s = [
            #      '$GPGGA',
            #      '115920.00',
            #      '4733.30295',
            #      'N',
            #      '00747.49585',
            #      'E',
            #      '1',
            #      '03',
            #      '2.72',
            #      '283.7',
            #      'M',
            #      '47.3',
            #      'M',
            #      '',
            #      '*57\r\n'
            #     ]

            # get time_utc
            # time_utc = s[1]
            time_utc = datetime.now(timezone.utc)

            # get latitude
            lat = decode(s[2])
            # get lat_direction
            lat_direction = s[3]
            # get longitude
            lon = decode(s[4])
            # get lon_direction
            lon_direction = s[5]
            # get altitude
            ele = s[9]
            gih = s[11]
            # get satelites
            sat = s[7].lstrip('0')
            # horizonlal dilution
            hdop = s[8]

        return(time_utc,
               lat,
               lat_direction,
               lon,
               lon_direction,
               ele,
               gih,
               sat,
               hdop)

    else:
        return 0


def decode(coord):

    """decode GPS coordinates to decimal notation"""

    # DDDMM.MMMMM -> DD deg MM.MMMMM min
    v = coord.split(".")
    head = v[0]
    tail = v[1]
    deg = head[0:-2]
    min = head[-2:]
    sec = "0." + tail
    sec = str(float(sec) * 60)
    dec = str(float(deg) + float(min)/60 + float(sec)/3600)

    return dec


def distance(origin, destination):

    """
    Calculate the Haversine distance.

    Parameters
    ----------
    origin : tuple of float
        (lat, long)
    destination : tuple of float
        (lat, long)

    Returns
    -------
    distance in meter : float

    Examples
    --------
    >>> origin = (48.1372, 11.5756)  # Munich
    >>> destination = (52.5186, 13.4083)  # Berlin
    >>> round(distance(origin, destination), 1)

    """

    lat1, lon1 = origin
    lat2, lon2 = destination

    # radius of the eart in m
    radius = 6371000

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = radius * c

    return d


def getCPMLev(cpm):

    """Get Radiation Levels"""

    # Standard values from the Nuclear Radiation Safety Guide
    cpm_lev = "Error"

    if cpm < 50:
        cpm_lev = "Normal"

    if cpm > 50:
        cpm_lev = "Medium"

    if cpm > 100:
        cpm_lev = "High"

    if cpm > 1000:
        cpm_lev = "Very High"

    if cpm > 2000:
        cpm_lev = "Extremely High"

    return cpm_lev


def writeInfluxDB(
    time,
    longitude,
    latitude,
    elevation,
    satellites,
    cpm,
    cpm_level
):

    json_body = [
        {
            "measurement": "GPSCPM",
            "tags": {
                "GeigerUnit": "CPM"
                },
            "fields": {
                "time": time,
                "latitude": float(latitude),
                "longitude": float(longitude),
                "elevation": float(elevation),
                "satellites": int(satellites),
                "cpm": int(cpm),
                "cpm_level": cpm_level,
        },
    ]

    return(influxdb.write_points(json_body))


# Wile we run and jump around in the field
while True:

    # to avoid amok runs
    sleep(0.1)

    # get cpm
    cpm = getCPM(geiger_ser)

    # append to cpm_array
    cpm_array.append(cpm)

    # get first waypoint
    if not gpgga_initial:

        eprint("\n"
                + "No GPS data [initial] ..."
                + "\n"
                + "\n" + "cpm_avg: " + str(round(listavg(cpm_array)))
                + "\n" + "cpm_min: " + str(min(cpm_array))
                + "\n" + "cpm_max: " + str(max(cpm_array))
                + "\n" + "cpm_lev: " + str(getCPMLev(max(cpm_array)))
        )

        gps_data_initial = gps_ser.readline().decode("utf-8")
        gpgga_initial = gpsGPGGA(gps_data_initial)

        if gpgga_initial:

                influx_status = writeInfluxDB(
                    gpgga_initial[0],
                    gpgga_initial[1],
                    gpgga_initial[3],
                    gpgga_initial[5],
                    gpgga_initial[7],
                    int(max(cpm_array)),
                    str(getCPMLev(max(cpm_array)))
                )

                print(influx_status)

        # do not remove me
        continue

     else:

         if not gpgga:

            eprint("\n"
                + "No GPS data ..."
                + "\n"
                + "\n" + "cpm_avg: " + str(round(listavg(cpm_array)))
                + "\n" + "cpm_min: " + str(min(cpm_array))
                + "\n" + "cpm_max: " + str(max(cpm_array))
                + "\n" + "cpm_lev: " + str(getCPMLev(max(cpm_array)))
            )

            gps_data = gps_ser.readline().decode("utf-8")
            gpgga = gpsGPGGA(gps_data)

            if gpgga:

                influx_status = writeInfluxDB(
                    gpgga[0],
                    gpgga[1],
                    gpgga[3],
                    gpgga[5],
                    gpgga[7],
                    int(max(cpm_array)),
                    str(getCPMLev(max(cpm_array)))
                )

                print(influx_status)

                # rinse and repete
                gpgga = []
                cpm_array = []
