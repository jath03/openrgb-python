#!/usr/bin/env python3
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor, DeviceType
import sensors
from time import sleep
from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetTemperature, NVML_TEMPERATURE_GPU
# import psutil


rgb = OpenRGBClient()
nvmlInit()

cooler = rgb.get_devices_by_type(DeviceType.DEVICE_TYPE_COOLER)[0]
gpu = rgb.get_devices_by_type(DeviceType.DEVICE_TYPE_GPU)[0]
# right_ram, left_ram = rgb.get_devices_by_type(DeviceType.DEVICE_TYPE_DRAM)

handle = nvmlDeviceGetHandleByIndex(0)


def temp_to_color(temp: int) -> (int, int):
    if temp < 40:
        return 0, 255
    elif temp < 70:
        return int((temp - 40) * 8), int((70 - temp) * 8)
    elif temp >= 70:
        return 255, 0


# right_ram.clear()
# left_ram.clear()


try:
    while True:
        ### CPU Temp
        sensors.init()
        chips = tuple(sensors.iter_detected_chips())
        # This sensor selection is based on my computer, I suggest using a debugger
        #   or print statements to figure out what chip and feature you want
        chip = [i for i in chips if i.prefix == b"k10temp"][0]

        feature = [i for i in chip if i.name == "temp1"][0]
        temp = feature.get_value()
        red, blue = temp_to_color(temp)
        cooler.set_led_color(1, RGBColor(red, 0, blue))
        cooler.set_led_color(2, RGBColor(red, 0, blue))

        ### GPU Temp
        temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
        red, blue = temp_to_color(temp)
        gpu.set_color(RGBColor(red, 0, blue))

        ### CPU Usage
        ### Commented out because it was setting too many values at once, causing a significant delay
        ###     between temperature change and color change that accumulated with each loop.
        # usage = psutil.cpu_percent()
        # if usage < 20:
        #     left_ram.set_color(RGBColor(0, 0, 0), end=4)
        #     left_ram.set_led_color(4, RGBColor(int(usage*10), 0, 0))
        # elif usage < 40:
        #     left_ram.set_color(RGBColor(0, 0, 0), end=3)
        #     left_ram.set_led_color(3, RGBColor(int((usage - 20)*10), 0, 0))
        #     left_ram.set_led_color(4, RGBColor(255, 0, 0))
        # elif usage < 60:
        #     left_ram.set_color(RGBColor(0, 0, 0), end=2)
        #     left_ram.set_led_color(2, RGBColor(int((usage - 40)*10), 0, 0))
        #     left_ram.set_color(RGBColor(0, 0, 0), start=3)
        # elif usage < 80:
        #     left_ram.set_led_color(0, RGBColor(0, 0, 0))
        #     left_ram.set_led_color(1, RGBColor(int((usage - 60)*10), 0, 0))
        #     left_ram.set_color(RGBColor(0, 0, 0), start=2)
        # else:
        #     left_ram.set_led_color(0, RGBColor(int((usage - 80)*10), 0, 0))
        #     left_ram.set_color(RGBColor(0, 0, 0), start=1)
        ### sleep is necessary to allow the sdk to set led values without creating a backup of
        ###     color change requests which causes the delay mentioned earlier.
        sleep(.2)
finally:
    sensors.cleanup()
