#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import serial
import signal
import gpxpy
import gpxpy.gpx
import sys
from time import sleep
from datetime import datetime, timezone
import math


# seconds to wait between mesurements
wait_sec = 5

# distance between waypoints in m
# use float
waypoint_distance = 5.0

# gps
gps_port = "/dev/ttyACM0"
gps_baudrate = 9600
gps_timeout = 0

# geiger
geiger_port = '/dev/ttyUSB0'
geiger_baudrate = 115200

time_utc = datetime.now(timezone.utc)

# initialize serial connections
gps_ser = serial.Serial(port=gps_port,
                        baudrate=gps_baudrate,
                        timeout=gps_timeout)

geiger_ser = serial.Serial(port=geiger_port,
                           baudrate=geiger_baudrate)
# some counters
gpgga_initial = 0
gpgga_first = []
gpgga_second = []
cpm_array = []

# initialize gpx file
gpx = gpxpy.gpx.GPX()
gpx.name = 'Geigerlog'
gpx.description = str(time_utc)

# Create first track in our GPX:
gpx_track = gpxpy.gpx.GPXTrack()
gpx_track.source = str(gps_port) + " (" + str(gps_baudrate) + ")"
gpx_track.description = "Geiger counter device: " \
    + str(geiger_port) + " (" + str(geiger_baudrate) + ")"
gpx_track.name = "Geigerlog"

gpx.tracks.append(gpx_track)
# Create first segment in our GPX track:
gpx_segment = gpxpy.gpx.GPXTrackSegment()
gpx_track.segments.append(gpx_segment)


# SIG handles
def handler(signum, frame):
    eprint("Ctrl-c was pressed. Do you really want to exit? y/n ")
    res = input()
    if res == 'y':
        print(gpx.to_xml())
        exit(1)


# initialize signal handler
signal.signal(signal.SIGINT, handler)


# print to stderr
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


# avg of a list
def listavg(lst):
    return sum(lst) / len(lst)


def getCPM(ser):                                # get CPM from device

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


def writeGPXWaypoint(gpgga, cpm, cpm_lev, desc):

    gpx_wps = gpxpy.gpx.GPXWaypoint()
    gpx_wps.time = gpgga[0]
    gpx_wps.latitude = gpgga[1]
    gpx_wps.longitude = gpgga[3]
    gpx_wps.elevation = gpgga[5]
    # gpx_wps.symbol = ""
    gpx_wps.name = str(cpm_lev) + ": " + str(cpm)
    gpx_wps.description = desc
    # append waypoint
    gpx.waypoints.append(gpx_wps)

    return 0


def writeGPXSegment(gpgga, cpm, cpm_lev):
    # append segmentpoint
    gpx_segment.points.append(
        gpxpy.gpx.GPXTrackPoint(
            time=gpgga[0],
            latitude=gpgga[1],
            longitude=gpgga[3],
            elevation=gpgga[5],
            horizontal_dilution=gpgga[7],
            name=str(cpm_lev) + ": " + str(cpm)
            ))

    return 0


# Wile we run and jump around in the field
while True:

    # to avoid amok runs
    sleep(0.1)

    # get cpm
    cpm = getCPM(geiger_ser)

    # append to cpm_array
    cpm_array.append(cpm)

    # get first waypoint
    if not gpgga_first:
        gps_data_first = gps_ser.readline().decode("utf-8")
        gpgga_first = gpsGPGGA(gps_data_first)
        # to avoid amok runs
        cpm_first = max(cpm_array)
        cpm_lev_first = getCPMLev(cpm_first)

        sleep(0.2)
        if not gpgga_first:
            eprint(
                "\n" + "Nooo, baby !!!, No GPS data [gpgga_first]"
                + "\n" + "cpm_avg: " + str(round(listavg(cpm_array)))
                + "\n" + "cpm_min: " + str(min(cpm_array))
                + "\n" + "cpm_max: " + str(max(cpm_array))
                + "\n" + "cpm_lev: " + str(getCPMLev(max(cpm_array)))
                )
            # do not remove me
            continue
        else:
            if gpgga_initial == 0:

                writeGPXWaypoint(gpgga_first,
                                 cpm_first,
                                 cpm_lev_first,
                                 "initial: " + str(gpgga_first[0]))

                writeGPXSegment(gpgga_first, cpm_first, cpm_lev_first)

                gpgga_initial = 1
            continue

    # get second waypoint
    if not gpgga_second:
        # write track
        gps_data_second = gps_ser.readline().decode("utf-8")
        gpgga_second = gpsGPGGA(gps_data_second)
        # to avoid amok runs
        cpm_second = max(cpm_array)
        cpm_lev_second = getCPMLev(cpm_first)
        sleep(0.2)

        if not gpgga_second:
            eprint(
                "\n" + "Nooo, baby !!!, No GPS data [gpgga_second]"
                + "\n" + "cpm_avg: " + str(round(listavg(cpm_array)))
                + "\n" + "cpm_min: " + str(min(cpm_array))
                + "\n" + "cpm_max: " + str(max(cpm_array))
                + "\n" + "cpm_lev: " + str(getCPMLev(max(cpm_array)))
                )
            # do not remove
            continue

    # calculate distance between waypoints
    dist = distance([float(gpgga_first[1]), float(gpgga_first[3])],
                    [float(gpgga_second[1]), float(gpgga_second[3])])

    # only write waypoints at a certain distance
    if dist < waypoint_distance:
        eprint(
            "\n" + "Nooo, baby !!!, "
            + "Distance from last waypoint is not sufficient:"
            + "\n" + "dist(m)     : " + str(round(dist, 2))
            + "\n" + "cpm_avg     : " + str(round(listavg(cpm_array)))
            + "\n" + "cpm_min     : " + str(min(cpm_array))
            + "\n" + "cpm_max     : " + str(max(cpm_array))
            + "\n" + "cpm_lev     : " + str(getCPMLev(max(cpm_array)))
            + "\n" + "counts      : " + str(len(cpm_array))
            + "\n" + "gpgga_first : "
            + "\n" + "gps_tutc    : " + str(gpgga_first[0])
            + "\n" + "gps_lat     : " + str(gpgga_first[1])
            + " " + str(gpgga_first[2])
            + "\n" + "gps_lon     : " + str(gpgga_first[3])
            + " " + str(gpgga_first[4])
            + "\n" + "gps_ele(m)  : " + str(gpgga_first[5])
            + "\n" + "gps_sat     : " + str(gpgga_first[6])
            + "\n" + "gpgga_second : "
            + "\n" + "gps_tutc    : " + str(gpgga_second[0])
            + "\n" + "gps_lat     : " + str(gpgga_second[1])
            + " " + str(gpgga_first[2])
            + "\n" + "gps_lon     : " + str(gpgga_second[3])
            + " " + str(gpgga_first[4])
            + "\n" + "gps_ele(m)  : " + str(gpgga_second[5])
            + "\n" + "gps_sat     : " + str(gpgga_second[6])
            + "\n"
        )
        # write second segment
        writeGPXSegment(gpgga_second, cpm_second, cpm_lev_second)

        # reset second
        gpgga_second = []
        continue
    else:
        eprint(
            "\n" + "Yeah, baby !!!, "
            + "Let's write a waypoint:"
            + "\n" + "dist(m)     : " + str(round(dist, 2))
            + "\n" + "cpm_avg     : " + str(round(listavg(cpm_array)))
            + "\n" + "cpm_min     : " + str(min(cpm_array))
            + "\n" + "cpm_max     : " + str(max(cpm_array))
            + "\n" + "cpm_lev     : " + str(getCPMLev(max(cpm_array)))
            + "\n" + "counts      : " + str(len(cpm_array))
            + "\n" + "gpgga_first : "
            + "\n" + "gps_tutc    : " + str(gpgga_first[0])
            + "\n" + "gps_lat     : " + str(gpgga_first[1])
            + " " + str(gpgga_first[2])
            + "\n" + "gps_lon     : " + str(gpgga_first[3])
            + " " + str(gpgga_first[4])
            + "\n" + "gps_ele(m)  : " + str(gpgga_first[5])
            + "\n" + "gps_sat     : " + str(gpgga_first[6])
            + "\n" + "gpgga_second : "
            + "\n" + "gps_tutc    : " + str(gpgga_second[0])
            + "\n" + "gps_lat     : " + str(gpgga_second[1])
            + " " + str(gpgga_first[2])
            + "\n" + "gps_lon     : " + str(gpgga_second[3])
            + " " + str(gpgga_first[4])
            + "\n" + "gps_ele(m)  : " + str(gpgga_second[5])
            + "\n" + "gps_sat     : " + str(gpgga_second[6])
            + "\n"
        )

        # write_waypoint
        # adding waypoints
        writeGPXWaypoint(
            gpgga_first,
            cpm_first,
            cpm_lev_first,
            str(gpgga_first[0]))

        writeGPXWaypoint(
            gpgga_second,
            cpm_second,
            cpm_lev_second,
            str(gpgga_second[0]))

    # rinse and repete
    if gpgga_first and gpgga_second:
        gpgga_first = []
        gpgga_second = []
        cpm_array = []
