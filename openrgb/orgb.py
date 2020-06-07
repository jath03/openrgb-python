#!/usr/bin/env python3
import struct
from openrgb import utils
from typing import List, Union
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
        if end == 0:
            end = len(self.leds)
        self.comms.send_header(
            self.id,
            utils.PacketType.NET_PACKET_ID_RGBCONTROLLER_UPDATELEDS,
            struct.calcsize(f"IH{3*(end - start)}b{(end - start)}x")
        )
        buff = struct.pack("H", end - start) + (color.pack())*(end - start)
        buff = struct.pack("I", len(buff)) + buff
        self.comms.sock.send(buff)

    def set_colors(self, colors: List[utils.RGBColor], start: int = 0, end: int = 0):
        '''
        Sets the LEDs colors between start and end

        :param colors: the list of colors, one per led
        :param start: the first LED to change
        :param end: the last LED to change
        '''
        if end == 0:
            end = len(self.leds)
        if len(colors) != (end - start):
            raise IndexError("Number of colors doesn't match number of LEDs")
        self.comms.send_header(
            self.id,
            utils.PacketType.NET_PACKET_ID_RGBCONTROLLER_UPDATELEDS,
            struct.calcsize(f"IH{3*(end - start)}b{(end - start)}x")
        )
        buff = struct.pack("H", end - start) + b''.join((color.pack() for color in colors))
        buff = struct.pack("I", len(buff)) + buff
        self.comms.sock.send(buff)

    def set_mode(self, mode: Union[int, str, utils.ModeData]):
        '''
        Sets the device's mode

        :param mode: the id, name, or the ModeData object itself to set as the mode
        '''
        if type(mode) == utils.ModeData:
            pass
        elif type(mode) == int:
            mode = self.modes[mode]
        elif type(mode) == str:
            mode = next((m for m in self.modes if m.name.lower() == mode.lower()))
        # print(mode)
        size, data = mode.pack()
        self.comms.send_header(
            self.id,
            utils.PacketType.NET_PACKET_ID_RGBCONTROLLER_UPDATEMODE,
            size
        )
        self.comms.sock.send(data)

    def set_custom_mode(self):
        self.comms.send_header(
            self.id,
            utils.PacketType.NET_PACKET_ID_RGBCONTROLLER_SETCUSTOMMODE,
            0
        )


class OpenRGBClient(utils.RGBObject):
    '''
    This is the only class you should ever need to instantiate.  It initializes
    the communication, gets the device information, sets the devices to the
    custom mode and creates Devices, Zones, and LEDs for you.
    '''

    def __init__(self, address: str = "127.0.0.1", port: int = 1337, name: str = "openrgb-python", custom: bool = True):
        '''
        :param address: the ip address of the SDK server
        :param port: the port of the SDK server
        :param name: the string that will be displayed on the OpenRGB SDK tab's list of clients
        :param custom: whether or not to set all your devices to custom control mode on initializtion
        '''
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
        while any((dev is None for dev in self.devices)):
            sleep(.2)
        if custom:
            for dev in self.devices:
                dev.set_custom_mode()

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

    def get_devices_by_type(self, type: utils.DeviceType) -> List[Device]:
        '''
        Gets a list of devices that are the same type as requested

        :param type: what type of device you want to get
        '''
        return [device for device in self.devices if device.type == type]
