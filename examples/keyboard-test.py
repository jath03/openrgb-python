#!/usr/bin/env python3
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor, DeviceType, ZoneType
from time import sleep

cli = OpenRGBClient()

keyboard = cli.get_devices_by_type(DeviceType.DEVICE_TYPE_KEYBOARD)[0]
keys_zone = [z for z in keyboard.zones if z.type == ZoneType.ZONE_TYPE_MATRIX][0]

while True:
    for color in (RGBColor(255, 0, 0), RGBColor(0, 255, 0), RGBColor(0, 0, 255), RGBColor(0, 0, 0)):
        for x in range(len(keys_zone.leds)):
            keys_zone.set_color(color, end=(x + 1))
            sleep(.3)
