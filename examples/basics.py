#!/usr/bin/env python3
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

client = OpenRGBClient()

print(client)

print(client.devices)

client.off()

client.set_color(RGBColor(0, 0, 255))
