#!/usr/bin/env python3
from ..openrgb import OpenRGBClient
from ..openrgb.utils import RGBColor, DeviceType
from time import sleep

client = OpenRGBClient()

print(client)

print(client.devices)

client.off()

for device in client.devices:
    device.set_color(RGBColor(255, 0, 0))
