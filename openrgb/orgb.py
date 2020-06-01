#!/usr/bin/env python3
import struct
from openrgb import utils
from typing import Callable, List, Union, Tuple
from openrgb.network import NetworkClient
# from dataclasses import dataclass
from time import sleep


class LED(utils.RGBObject):
    '''
    A class to represent individual LEDs
    '''
    def __init__(self, data: utils.LEDData, led_id: int, device_id: int, network_client: NetworkClient):
        self.name = data.name
        self.id = led_id
        self.device_id = device_id
        self.comms = network_client

    def set_color(self, color: utils.RGBColor):
        '''
        Sets the color of the LED

        :param color: the color to set the LED to
        '''
        self.comms.send_header(self.device_id, utils.PacketType.NET_PACKET_ID_RGBCONTROLLER_UPDATESINGLELED, struct.calcsize("i3bx"))
        buff = struct.pack("i", self.id) + color.pack()
        self.comms.sock.send(buff)


class Zone(utils.RGBObject):
    '''
    A class to represent a zone
    '''
    def __init__(self, data: utils.ZoneData, zone_id: int, device_id: int, network_client: NetworkClient):
        self.name = data.name
        self.type = data.zone_type
        self.leds = [LED(data.leds[x], x, device_id, network_client) for x in range(len(data.leds))]
        self.mat_width = data.mat_width
        self.mat_height = data.mat_height
        self.matrix_map = data.matrix_map
        self.colors = data.colors
        self.device_id = device_id
        self.comms = network_client
        self.id = zone_id

    def set_color(self, color: utils.RGBColor, start: int = 0, end: int = 0):
        '''
        Sets the LEDs color in the zone between start and end

        :param color: the color to set the leds to
        :param start: the first LED to change
        :param end: the last LED to change
        '''
        if end == 0:
            end = len(self.leds)
        self.comms.send_header(self.device_id, utils.PacketType.NET_PACKET_ID_RGBCONTROLLER_UPDATEZONELEDS, struct.calcsize(f"IIH{3*(end - start)}b{(end - start)}x"))
        buff = struct.pack("IH", self.id, end - start) + (color.pack())*(end - start)
        buff = struct.pack("I", len(buff)) + buff
        self.comms.sock.send(buff)

    def set_colors(self, colors: List[utils.RGBColor], start: int = 0, end: int = 0):
        '''
        Sets the LEDs colors in the zone between start and end

        :param colors: the list of colors, one per led
        :param start: the first LED to change
        :param end: the last LED to change
        '''
        if end == 0:
            end = len(self.leds)
        if len(colors) != (end - start):
            raise IndexError("Number of colors doesn't match number of LEDs")
        self.comms.send_header(self.device_id, utils.PacketType.NET_PACKET_ID_RGBCONTROLLER_UPDATEZONELEDS, struct.calcsize(f"IIH{3*(end - start)}b{(end - start)}x"))
        buff = struct.pack("IH", self.id, end - start) + b''.join((color.pack() for color in colors))
        buff = struct.pack("I", len(buff)) + buff
        self.comms.sock.send(buff)


class Device(utils.RGBObject):
    '''
    A class to represent a RGB Device
    '''
    def __init__(self, data: utils.ControllerData, device_id: int, network_client: NetworkClient):
        self.name = data.name
        self.metadata = data.metadata
        self.type = data.device_type
        self.leds = [LED(data.leds[x], x, device_id, network_client) for x in range(len(data.leds))]
        self.zones = [Zone(data.zones[x], x, device_id, network_client) for x in range(len(data.zones))]
        self.modes = data.modes
        self.colors = data.colors
        self.active_mode = data.active_mode
        self.id = device_id
        self.comms = network_client

    def set_color(self, color: utils.RGBColor, start: int = 0, end: int = 0):
        '''
        Sets the LEDs color between start and end

        :param color: the color to set the leds to
        :param start: the first LED to change
        :param end: the last LED to change
        '''
        self._set_color(
            self.leds,
            utils.PacketType.NET_PACKET_ID_RGBCONTROLLER_UPDATELEDS,
            color,
            start,
            end
        )

    def set_colors(self, colors: List[utils.RGBColor], start: int = 0, end: int = 0):
        '''
        Sets the LEDs colors between start and end

        :param colors: the list of colors, one per led
        :param start: the first LED to change
        :param end: the last LED to change
        '''
        self._set_colors(
            self.leds,
            utils.PacketType.NET_PACKET_ID_RGBCONTROLLER_UPDATELEDS,
            colors,
            start,
            end
        )
    # def set_mode(self, )


class OpenRGBClient(object):
    '''
    This is the only class you should ever need to instantiate.  It initializes the communication, gets the device information, and creates Devices, Zones, and LEDs for you.
    '''
    def __init__(self, address: str = "127.0.0.1", port: int = 1337, name: str = "openrgb-python"):
        self.comms = NetworkClient(self._callback, address, port, name)
        self.address = address
        self.port = port
        self.name = name
        self.device_num = 0
        while self.device_num == 0:
            sleep(.2)
        self.devices = [None for x in range(self.device_num)]
        for x in range(self.device_num):
            self.comms.requestDeviceData(x)
        sleep(1) # Giving the client time to recieve the device data

    def __repr__(self):
        return f"OpenRGBClient(address={self.address}, port={self.port}, name={self.name})"

    def _callback(self, device: int, type: int, data):
        if type == utils.PacketType.NET_PACKET_ID_REQUEST_CONTROLLER_COUNT:
            self.device_num = data
        elif type == utils.PacketType.NET_PACKET_ID_REQUEST_CONTROLLER_DATA:
            if self.devices[device] is None:
                self.devices[device] = Device(data, device, self.comms)
            else:
                self.devices[device].data = data

    def set_color(self, color: utils.RGBColor):
        '''
        Sets the color of every device.

        :param color: the color to set the devices to
        '''
        for device in self.devices:
            device.set_color(color)

    def clear(self):
        '''
        Turns all of the LEDs off
        '''
        self.set_color(utils.RGBColor(0, 0, 0))

    def off(self):
        '''
        See OpenRGBClient.clear
        '''
        self.clear()

    def get_devices_by_type(self, type: utils.DeviceType) -> List[Device]:
        '''
        Gets a list of devices that are the same type as requested

        :param type: what type of device you want to get
        '''
        return [device for device in self.devices if device.type == type]
