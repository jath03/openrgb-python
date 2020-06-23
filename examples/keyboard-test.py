#!/usr/bin/env python3
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor, DeviceType, ZoneType
from time import sleep

cli = OpenRGBClient()

keyboard = cli.get_devices_by_type(DeviceType.DEVICE_TYPE_KEYBOARD)[0]
keys_zone = [z for z in keyboard.zones if z.zone_type == ZoneType.ZONE_TYPE_MATRIX][0]

try:
    keyboard.set_mode("direct")
except:
    keyboard.set_mode(0)
while True:
    for color in (RGBColor(255, 0, 0), RGBColor(0, 255, 0), RGBColor(0, 0, 255), RGBColor(0, 0, 0)):
        for x in range(len(keys_zone.leds)):
            keys_zone.set_color(color, end=x)
            sleep(.3)
