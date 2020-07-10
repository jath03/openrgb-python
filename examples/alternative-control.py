#!/usr/bin/env python3

# Happy belated 4th of July!

from openrgb import OpenRGBClient
from openrgb.utils import RGBColor
from time import sleep

cli = OpenRGBClient()

offsets = [(0, 1, 2), (1, 2, 0), (2, 0, 1)]


while True:
    for offset in offsets:
        for device in cli.devices:
            # Setting every third color red
            for x in range(offset[0], len(device.colors), 3):
                device.colors[x] = RGBColor(255, 0, 0)
            # Setting every third color white
            for x in range(offset[1], len(device.colors), 3):
                device.colors[x] = RGBColor(255, 255, 255)
            # Setting every third color blue
            for x in range(offset[2], len(device.colors), 3):
                device.colors[x] = RGBColor(0, 0, 255)
        cli.show()  # Updates all devices
        sleep(.5)
