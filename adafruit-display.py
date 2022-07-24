#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2017 Tony DiCola for Adafruit Industries
# SPDX-FileCopyrightText: 2017 James DeVito for Adafruit Industries
# SPDX-License-Identifier: MIT

# This example is for use on (Linux) computers that are using CPython with
# Adafruit Blinka to support CircuitPython libraries. CircuitPython does
# not support PIL/pillow (python imaging library)!

import time
import subprocess

from board import SCL, SDA
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

wait = 7

# Create the I2C interface.
i2c = busio.I2C(SCL, SDA)

# Create the SSD1306 OLED class.
# The first two parameters are the pixel width and pixel height.  Change these
# to the right size for your display!
disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

# Clear display.
disp.fill(0)
disp.show()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new("1", (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height - padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0


# Load default font.
font = ImageFont.load_default()

# Alternatively load a TTF font.  Make sure the .ttf font file is in the
# same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
# font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 9)

while True:

    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    # Shell scripts for system monitoring from here:
    # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    #cmd = "hostname -I | cut -d' ' -f1"

    cmd = "ip addr show wlan0 | head -3 | tail -1 | awk '{print $2}'"
    IP0 = subprocess.check_output(cmd, shell=True).decode("utf-8")

    cmd = "ip addr show eth0 | head -3 | tail -1 | awk '{print $2}'"
    IP1 = subprocess.check_output(cmd, shell=True).decode("utf-8")

    cmd = "ip addr show wlan0 | head -2 | tail -1 | awk '{print $2}'"
    MAC0 = subprocess.check_output(cmd, shell=True).decode("utf-8")

    cmd = "ip addr show eth0 | head -2 | tail -1 | awk '{print $2}'"
    MAC1 = subprocess.check_output(cmd, shell=True).decode("utf-8")



    # Write four lines of text.

    if MAC0 != IP0:
      draw.text((x, top + 0), "I0: " + IP0, font=font, fill=255)
      draw.text((x, top + 8), "M0: " + MAC0, font=font, fill=255)
    else:
      draw.text((x, top + 0), "M0: " + MAC0, font=font, fill=255)

    if MAC1 != IP1:
      draw.text((x, top + 16), "I1: " + IP1, font=font, fill=255)
      draw.text((x, top + 25), "M1: " + MAC1, font=font, fill=255)
    else:
      if MAC0 == IP0:
        draw.text((x, top + 8), "M1: " + MAC1, font=font, fill=255)
      else:
        draw.text((x, top + 16), "M1: " + MAC1, font=font, fill=255)

    # Display image.
    disp.image(image)
    disp.show()
    time.sleep(wait)

    #cmd = 'cut -f 1 -d " " /proc/loadavg'
    cmd = 'iostat -c -o JSON | grep avg-cpu | awk \'{print $3}\' |sed s/,/%/g'
    CPU = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB %.0f%%\", $3,$2,$3*100/$2 }'"
    MemUsage = subprocess.check_output(cmd, shell=True).decode("utf-8")
    #cmd = 'df -h | awk \'$NF=="/"{printf "Disk: %d/%d GB %s", $3,$2,$5}\''
    cmd = 'df -h | awk \'$NF=="/"{printf "Disk: %d/%d/%d GB %s", $2,$3,$4,$5}\''
    Disk = subprocess.check_output(cmd, shell=True).decode("utf-8")

    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    draw.text((x, top + 0), "CPU: " + CPU, font=font, fill=255)
    draw.text((x, top + 8), MemUsage, font=font, fill=255)
    draw.text((x, top + 16), Disk, font=font, fill=255)

    # Display image.
    disp.image(image)
    disp.show()
    time.sleep(wait)

    cmd = 'ls /dev/ttyACM0 2>/dev/null || echo N/A'
    GPS = subprocess.check_output(cmd, shell=True).decode("utf-8")

    cmd = 'ls /dev/ttyUSB0 2>/dev/null || echo N/A'
    CNT = subprocess.check_output(cmd, shell=True).decode("utf-8")

    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    draw.text((x, top + 0), "GPS: " + GPS, font=font, fill=255)
    draw.text((x, top + 8), "CNT: " + CNT, font=font, fill=255)

    # Display image.
    disp.image(image)
    disp.show()
    time.sleep(wait)

    cmd = 'ps ax | grep influxd | grep -v grep | awk \'{ print $1}\''
    influxd = subprocess.check_output(cmd, shell=True).decode("utf-8")

    cmd = 'ps ax | grep grafana | grep -v grep | awk \'{ print $1}\''
    grafana = subprocess.check_output(cmd, shell=True).decode("utf-8")

    cmd = 'ps ax | grep sshd | grep -v grep | awk \'{ print $1}\''
    sshd = subprocess.check_output(cmd, shell=True).decode("utf-8")

    cmd = 'ps ax | grep influx-radiation-tracker | grep -v grep | awk \'{ print $1}\''
    script = subprocess.check_output(cmd, shell=True).decode("utf-8")


    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    draw.text((x, top + 0), "grafana: " + grafana, font=font, fill=255)
    draw.text((x, top + 8), "influxd: " + influxd, font=font, fill=255)
    draw.text((x, top + 16), "sshd: " + sshd, font=font, fill=255)
    draw.text((x, top + 25), "script: " + script, font=font, fill=255)

    # Display image.
    disp.image(image)
    disp.show()
    time.sleep(wait)

# 
