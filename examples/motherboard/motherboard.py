#!/usr/bin/env python3
# This Example grabs perfmon counters (Processor Performance %) as an indicator of CPU Boost
# and updates via direct ARGB to a led strip
# Sample uses Aorus Elite Wifi with Lian Li Lancool II Casae on the "Digital Bottom" 3-pin ARGB output

from openrgb import OpenRGBClient
from openrgb.utils import DeviceType
from openrgb.utils import RGBColor
#import wmi
import winstats

maxtemp = 100
mintemp = 30
maxperf = 125
minperf = 95

ledstripsize=19

red = RGBColor(255, 0, 0)
blue=RGBColor(0,0,255)
zonenumber=0
#myColorList = red, blue, red, blue, red, blue, red, red, blue, blue, red, blue, red, blue

cli = OpenRGBClient()
print(cli)
mobo = cli.get_devices_by_type(DeviceType.MOTHERBOARD)[0]
print(mobo)
mobo.set_mode('direct')
mobo.zones[zonenumber].resize(ledstripsize)
print(mobo.zones[zonenumber])

myLeds = mobo.zones[zonenumber].leds
for i in myLeds:
    i.set_color(red)

step = ((maxperf-minperf)/len(myLeds))

while True: 
    procperf = winstats.get_perf_data(r'\Processor Information(_Total)\% Processor Performance',fmts='double',delay=1000)
    j = int((procperf[0] - minperf) / step)
    print(j, procperf)
    for i in range(len(myLeds)):
        if i <= j:
            myLeds[i].set_color(red)
        else:
            myLeds[i].set_color(blue)