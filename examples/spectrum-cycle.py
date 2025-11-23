#!/usr/bin/env python3
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor
import time

client = OpenRGBClient()

print(client)

print(client.devices)

client.clear()

while True:
    for x in range(360):
        client.set_color(RGBColor.fromHSV(x, 100, 100), fast=True)
        time.sleep(.05)
