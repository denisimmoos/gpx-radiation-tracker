#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import serial
import signal
import gpxpy
import gpxpy.gpx
import sys
from time import sleep
from datetime import datetime, timezone

# seconds to wait between mesurements
wait_sec = 5

# gps
gps_port = "/dev/ttyACM0"
gps_baudrate = 9600
gps_timeout = 0

# geiger
geiger_port = '/dev/ttyUSB0'
geiger_baudrate = 115200

# array to collect TXT information
GPTXT = []

# initialize gpx file
gpx = gpxpy.gpx.GPX()
gpx.name = 'Geigerlog'
gpx.description = ''

# Create first track in our GPX:
gpx_track = gpxpy.gpx.GPXTrack()
gpx_track.source = str(geiger_port) + " (" + str(gps_baudrate) + ")"
gpx.tracks.append(gpx_track)

# Create first segment in our GPX track:
gpx_segment = gpxpy.gpx.GPXTrackSegment()
gpx_track.segments.append(gpx_segment)


# print to stdout
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


# SIG handles
def handler(signum, frame):
    eprint("Ctrl-c was pressed. Do you really want to exit? y/n ")
    res = input()
    if res == 'y':
        gpx_track.description = "\n".join(GPTXT)
        print(gpx.to_xml())
        exit(1)


# initialize signal handler
signal.signal(signal.SIGINT, handler)


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


# writeGPS
def writeGPX(data, cpm):

    # Standard values from the Nuclear Radiation Safety Guide
    if cpm < 50:
        cpm_level = "Normal"

    if cpm > 50:
        cpm_level = "Medium"

    if cpm > 100:
        cpm_level = "High"

    if cpm > 1000:
        cpm_level = "Very High"

    if cpm > 2000:
        cpm_level = "Extremely High"

    # get device info
    if "$GPTXT" in data:
        if "unknown" not in data:
            GPTXT.append(data.split(",")[4].split("*")[0])

    # get GPS info
    if "$GPGGA" in data:
        s = data.split(",")

        # print(s)
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
        # print(s)

        # get time in utc
        time_utc = datetime.now(timezone.utc)

        # check if the data is valid
        if s[6] == "0":
            eprint("no satellite data available")
            # print Radiation cpm_level
            eprint("radiation_level (" + cpm_level + "): " + str(cpm))
            return

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

        hdop = s[8]

        desc = "time_utc        : " + str(time_utc) + "\n"
        desc += "lat   (decimal): " + lat + " " + lat_direction + "\n"
        desc += "lon   (decimal): " + lon + " " + lon_direction + "\n"
        desc += "ele         (m): " + ele + "\n"
        desc += "sat         (c): " + sat + "\n"
        desc += "hdop           : " + hdop + "\n"
        desc += "url            : " + lat + "," + lon + "\n"
        desc += "cpm            : " + str(cpm) + "\n"
        desc += "radiation_level: " + str(cpm_level) + "\n"

        eprint(desc)

        # adding waypoints
        gpx_wps = gpxpy.gpx.GPXWaypoint()
        gpx_wps.elevation = ele
        gpx_wps.latitude = lat
        gpx_wps.longitude = lon
        #gpx_wps.symbol = "https://img.icons8.com/external-flaticons-flat-flat-icons/64/000000/external-radioactive-industry-flaticons-flat-flat-icons.png"
        gpx_wps.name = cpm_level + ": " + str(cpm)
        gpx_wps.description = desc
        gpx_wps.time = time_utc

        # append waypoint
        gpx.waypoints.append(gpx_wps)


        # append segmentpoint
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(
            lat,
            lon,
            elevation=ele,
            time=time_utc,
            horizontal_dilution=hdop,
            ))

        sleep(wait_sec)


def decode(coord):
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


# initialize serial connections
gps_ser = serial.Serial(port=gps_port,
                        baudrate=gps_baudrate,
                        timeout=gps_timeout)

geiger_ser = serial.Serial(port=geiger_port,
                           baudrate=geiger_baudrate)

# make it pretty
eprint("\n")

while True:
    gps_data = gps_ser.readline().decode("utf-8")
    geiger_cpm = getCPM(geiger_ser)
    writeGPX(gps_data, geiger_cpm)
