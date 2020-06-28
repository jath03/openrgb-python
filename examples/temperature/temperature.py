#!/usr/bin/env python3
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor, DeviceType
from time import sleep
from py3nvml.py3nvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetTemperature, NVML_TEMPERATURE_GPU
import psutil
from typing import Tuple


def initRGB():
    # Getting this script ready to be run as a service. Waiting for the sdk to start.
    while True:
        try:
            cli = OpenRGBClient()
            break
        except ConnectionRefusedError:
            sleep(5)
            continue
    cooler = cli.get_devices_by_type(DeviceType.DEVICE_TYPE_COOLER)[0]
    gpu = cli.get_devices_by_type(DeviceType.DEVICE_TYPE_GPU)[0]
    # right_ram, left_ram = cli.get_devices_by_type(DeviceType.DEVICE_TYPE_DRAM)

    # right_ram.clear()
    # left_ram.clear()


    # To make sure the devices are in the right mode, and to work around a problem
    #   where the gpu won't change colors until switched out of static mode and
    #   then back into static mode.
    cooler.set_mode(0)  # Direct mode
    gpu.set_mode(1)  # Anything would work, this is breathing in my setup
    sleep(.1)
    gpu.set_mode(0)  # Static mode.  My GPU doesn't have a direct mode.
    return cooler, gpu


nvmlInit()


handle = nvmlDeviceGetHandleByIndex(0)


def temp_to_color(temp: int, min: int, max: int) -> Tuple[int, int]:
    multiplier = 240/(max - min)
    if temp < min:
        return 0, 255
    elif temp < max:
        return int((temp - min) * multiplier), int((max - temp) * multiplier)
    elif temp >= max:
        return 255, 0

cooler, gpu = initRGB()

while True:
    try:
        ### CPU Temp
        temp = psutil.sensors_temperatures()['k10temp'][-1].current

        red, blue = temp_to_color(temp, 45, 75)
        cooler.set_color(RGBColor(red, 0, blue))

        ### GPU Temp
        temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
        red, blue = temp_to_color(temp, 35, 65)
        gpu.set_color(RGBColor(red, 0, blue))

        ### RAM Usage
        ### Works fine
        # usage = psutil.virtual_memory().percent
        # if usage < 20:
        #     right_ram.set_color(RGBColor(0, 0, 0), end=4)
        #     right_ram.leds[4].set_color(RGBColor(0, 0, int(usage*10)))
        # elif usage < 40:
        #     right_ram.set_color(RGBColor(0, 0, 0), end=3)
        #     right_ram.leds[3].set_color(RGBColor(0, 0, int((usage - 20)*10)))
        #     right_ram.leds[4].set_color(RGBColor(0, 0, 255))
        # elif usage < 60:
        #     right_ram.set_color(RGBColor(0, 0, 0), end=2)
        #     right_ram.leds[2].set_color(RGBColor(0, 0, int((usage - 40)*10)))
        #     right_ram.set_color(RGBColor(0, 0, 255), start=3)
        # elif usage < 80:
        #     right_ram.set_color(RGBColor(0, 0, 255), start=2)
        #     right_ram.leds[0].set_color(RGBColor(0, 0, 0))
        #     right_ram.leds[1].set_color(RGBColor(0, 0, int((usage - 60)*10)))
        # else:
        #     right_ram.set_color(RGBColor(0, 0, 255), start=1)
        #     right_ram.leds[0].set_color(RGBColor(0, 0, int((usage - 80)*10)))
    except (ConnectionResetError, BrokenPipeError, TimeoutError) as e:
        print(str(e) + " during main loop")
        print("Trying to reconnect...")
        cooler, gpu = initRGB()
