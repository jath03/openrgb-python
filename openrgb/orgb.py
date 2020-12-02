#!/usr/bin/env python3
import struct
from openrgb import utils
from typing import List, Union, Optional
from openrgb.network import NetworkClient
# from dataclasses import dataclass
from time import sleep
from os import environ


class LED(utils.RGBObject):
    '''
    A class to represent individual LEDs
    '''

    def __init__(self, data: utils.LEDData, color: utils.RGBColor, led_id: int, device_id: int, network_client: NetworkClient):
        self.name = data.name
        self.colors = [color]
        self._colors = self.colors[:]
        self.id = led_id
        self.device_id = device_id
        self.comms = network_client

    def set_color(self, color: utils.RGBColor, fast: bool = False):
        '''
        Sets the color of the LED

        :param color: the color to set the LED to
        :param fast: If you care more about quickly setting colors than having correct internal state data, then set :code:`fast` to :code:`True`
        '''
        self.comms.send_header(
            self.device_id,
            utils.PacketType.RGBCONTROLLER_UPDATESINGLELED,
            struct.calcsize("i3bx")
        )
        buff = struct.pack("i", self.id) + color.pack()
        self.comms.send_data(buff)
        if not fast:
            self.update()


class Zone(utils.RGBContainer):
    '''
    A class to represent a zone
    '''

    def __init__(self, data: utils.ZoneData, zone_id: int, device_id: int, network_client: NetworkClient):
        self.name = data.name
        self.type = data.zone_type
        self.leds = [LED(data.leds[x], data.colors[x], x + data.start_idx, device_id, network_client) for x in range(len(data.leds))]
        self.mat_width = data.mat_width
        self.mat_height = data.mat_height
        self.matrix_map = data.matrix_map
        self.colors = data.colors
        self._colors = self.colors[:]
        self.device_id = device_id
        self.comms = network_client
        self.id = zone_id

    def set_color(self, color: utils.RGBColor, start: int = 0, end: int = 0, fast: bool = False):
        '''
        Sets the LEDs' color in the zone between start and end

        :param color: the color to set the LEDs to
        :param start: the first LED to change
        :param end: the first unchanged LED
        :param fast: If you care more about quickly setting colors than having correct internal state data, then set :code:`fast` to :code:`True`
        '''
        if end == 0:
            end = len(self.leds)
        self.comms.send_header(
            self.device_id,
            utils.PacketType.RGBCONTROLLER_UPDATEZONELEDS,
            struct.calcsize(f"IiH{3*(end)}b{(end)}x")
        )
        buff = struct.pack("iH", self.id, end) + b''.join((color.pack() for color in self._colors[:start])) + (color.pack())*(end - start)
        buff = struct.pack("I", len(buff)) + buff
        self.comms.send_data(buff)
        if not fast:
            self.update()

    def set_colors(self, colors: List[utils.RGBColor], start: int = 0, end: int = 0, fast: bool = False):
        '''
        Sets the LEDs' colors in the zone between start and end

        :param colors: the list of colors, one per LED
        :param start: the first LED to change
        :param end: the first unchanged LED
        :param fast: If you care more about quickly setting colors than having correct internal state data, then set :code:`fast` to :code:`True`
        '''
        if end == 0:
            end = len(self.leds)
        if len(colors) != (end - start):
            raise IndexError("Number of colors doesn't match number of LEDs")
        self.comms.send_header(
            self.device_id,
            utils.PacketType.RGBCONTROLLER_UPDATEZONELEDS,
            struct.calcsize(f"IIH{3*(end)}b{(end)}x")
        )
        buff = struct.pack("IH", self.id, end) + b''.join((color.pack() for color in self._colors[:start])) + b''.join((color.pack() for color in colors))
        buff = struct.pack("I", len(buff)) + buff
        self.comms.send_data(buff)
        if not fast:
            self.update()

    def resize(self, size: int):
        '''
        Resizes the zone. Required to control addressable leds in Direct mode.

        :param size: the number of leds in the zone
        '''
        self.comms.send_header(
            self.device_id,
            utils.PacketType.RGBCONTROLLER_RESIZEZONE,
            struct.calcsize("ii")
        )
        self.comms.send_data(struct.pack("ii", self.id, size))
        self.update()


class Device(utils.RGBContainer):
    '''
    A class to represent an RGB Device
    '''

    def __init__(self, data: utils.ControllerData, device_id: int, network_client: NetworkClient):
        self.name = data.name
        self.metadata = data.metadata
        self.type = data.device_type
        self.leds = [LED(data.leds[x], data.colors[x], x, device_id, network_client) for x in range(len(data.leds))]
        self.zones = [Zone(data.zones[x], x, device_id, network_client) for x in range(len(data.zones))]
        self.modes = data.modes
        self.colors = data.colors
        self._colors = self.colors[:]
        self.active_mode = data.active_mode
        self.data = data
        self.id = device_id
        self.device_id = device_id
        self.comms = network_client

    def set_color(self, color: utils.RGBColor, start: int = 0, end: int = 0, fast: bool = False):
        '''
        Sets the LEDs' color between start and end

        :param color: the color to set the LED(s) to
        :param start: the first LED to change
        :param end: the first unchanged LED
        :param fast: If you care more about quickly setting colors than having correct internal state data, then set :code:`fast` to :code:`True`
        '''
        if end == 0:
            end = len(self.leds)
        self.comms.send_header(
            self.id,
            utils.PacketType.RGBCONTROLLER_UPDATELEDS,
            struct.calcsize(f"IH{3*(end)}b{(end)}x")
        )
        buff = struct.pack("H", end) + b''.join((color.pack() for color in self._colors[:start])) + (color.pack())*(end - start)
        buff = struct.pack("I", len(buff)) + buff
        self.comms.send_data(buff)
        if not fast:
            self.update()

    def set_colors(self, colors: List[utils.RGBColor], start: int = 0, end: int = 0, fast: bool = False):
        '''
        Sets the LEDs' colors between start and end

        :param colors: the list of colors, one per LED
        :param start: the first LED to change
        :param end: the first unchanged LED
        :param fast: If you care more about quickly setting colors than having correct internal state data, then set :code:`fast` to :code:`True`
        '''
        if end == 0:
            end = len(self.leds)
        if len(colors) != (end - start):
            raise IndexError("Number of colors doesn't match number of LEDs")
        self.comms.send_header(
            self.id,
            utils.PacketType.RGBCONTROLLER_UPDATELEDS,
            struct.calcsize(f"IH{3*(end)}b{(end)}x")
        )
        buff = struct.pack("H", end) + b''.join((color.pack() for color in self._colors[:start])) + b''.join((color.pack() for color in colors))
        buff = struct.pack("I", len(buff)) + buff
        self.comms.send_data(buff)
        if not fast:
            self.update()

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
        data = mode.pack()
        self.comms.send_header(
            self.id,
            utils.PacketType.RGBCONTROLLER_UPDATEMODE,
            len(data)
        )
        self.comms.send_data(data)
        self.update()

    def set_custom_mode(self):
        self.comms.send_header(
            self.id,
            utils.PacketType.RGBCONTROLLER_SETCUSTOMMODE,
            0
        )


class OpenRGBClient(utils.RGBObject):
    '''
    This is the only class you should need to manually instantiate.  It
    initializes the communication, gets the device information, and creates
    Devices, Zones, and LEDs for you.
    '''

    def __init__(self, address: str = "127.0.0.1", port: int = 6742, name: str = "openrgb-python", protocol_version: int = None):
        '''
        :param address: the ip address of the SDK server
        :param port: the port of the SDK server
        :param name: the string that will be displayed on the OpenRGB SDK tab's list of clients
        '''
        self.device_num = 0
        self.devices = []
        self.comms = NetworkClient(self._callback, address, port, name, protocol_version)
        self.address = address
        self.port = port
        self.name = name
        self.comms.requestDeviceNum()
        while any((dev is None for dev in self.devices)):
            sleep(.2)

    def __repr__(self):
        return f"OpenRGBClient(address={self.address}, port={self.port}, name={self.name})"

    def _callback(self, device: int, type: int, data: Optional[Union[int, utils.ControllerData]]):
        if type == utils.PacketType.REQUEST_CONTROLLER_COUNT:
            if data != self.device_num or data != len(self.devices):
                self.device_num = data
                self.devices = [None for x in range(self.device_num)]
                for x in range(self.device_num):
                    self.comms.requestDeviceData(x)
        elif type == utils.PacketType.REQUEST_CONTROLLER_DATA:
            try:
                if self.devices[device] is None:
                    self.devices[device] = Device(data, device, self.comms)
                else:
                    self.devices[device].__init__(data, device, self.comms)
            except IndexError:
                self.comms.requestDeviceNum()
        elif type == utils.PacketType.DEVICE_LIST_UPDATED:
            self.device_num = 0
            self.comms.requestDeviceNum()

    def set_color(self, color: utils.RGBColor, fast: bool = False):
        '''
        Sets the color of every device.

        :param color: the color to set the devices to
        :param fast: If you care more about quickly setting colors than having correct internal state data, then set :code:`fast` to :code:`True`
        '''
        for device in self.devices:
            device.set_color(color, fast=fast)

    def get_devices_by_type(self, type: utils.DeviceType) -> List[Device]:
        '''
        Gets a list of devices that are the same type as requested

        :param type: what type of device you want to get
        '''
        return [device for device in self.devices if device.type == type]

    def load_profile(self, name: str, directory: str = ''):
        '''
        Loads an OpenRGB profile file

        :param name: the name of the profile
        :param directory: what directory the profile is in.  Defaults to HOME/.config/OpenRGB
        '''
        if directory == '':
            directory = environ['HOME'].rstrip("/") + "/.config/OpenRGB"
        with open(f'{directory}/{name}.orp', 'rb') as f:
            controllers = utils.Profile.unpack(f).controllers
            pairs = []
            for device in self.devices:
                for new_controller in controllers:
                    if new_controller.name == device.name \
                            and new_controller.device_type == device.type \
                            and new_controller.metadata.description == device.metadata.description:
                        controllers.remove(new_controller)
                        pairs.append((new_controller, device))
            # print("Pairs:")
            for new_controller, device in pairs:
                # print(device.name, new_controller.name)
                if new_controller.colors != device.colors:
                    device.set_colors(new_controller.colors)
                # print(new_controller.active_mode)
                if new_controller.active_mode != device.active_mode:
                    device.set_mode(new_controller.active_mode)

    def save_profile(self, name: str, directory: str = ''):
        '''
        Saves the current state of all of your devices to an OpenRGB profile
        file

        :param name: the name of the profile to save
        :param directory: what directory to save the profile in.  Defaults to HOME/.config/OpenRGB
        '''
        self.get_device_info()
        if directory == '':
            directory = environ['HOME'].rstrip("/") + "/.config/OpenRGB"
        with open(f'{directory.rstrip("/")}/{name}.orp', 'wb') as f:
            f.write(utils.Profile([dev.data for dev in self.devices]).pack(0))

    def update(self):
        '''
        Gets the current state of your devices from the SDK server, which is
        useful if you change something from the gui or another SDK client and
        need to sync up the changes.
        '''
        self.comms.requestDeviceNum()
        for x in range(self.device_num):
            self.comms.requestDeviceData(x)

    def show(self, fast: bool = False, force: bool = False):
        '''
        Shows all devices

        :param fast: If you care more about quickly setting colors than having correct internal state data, then set :code:`fast` to :code:`True`
        :param force: Sets all colors rather than trying to only set the ones that have been changed
        '''
        for dev in self.devices:
            dev.show(True, force)
        if not fast:
            self.update()

    def connect(self):
        '''Connects to the OpenRGB SDK'''
        self.comms.start_connection()

    def disconnect(self):
        '''Disconnects from the OpenRGB SDK'''
        self.comms.stop_connection()

    @property
    def protocol_version(self):
        '''The protocol version of the connected SDK server'''
        return self.comms.protocol_version

    @protocol_version.setter
    def protocol_version(self, version: int):
        '''Sets the procol version of the connected SDK server'''
        if version <= self.comms.max_protocol_version:
            self.comms.protocol_version = version
        else:
            raise ValueError(f"version {version} is greater than maximum supported version {self.comms.max_protocol_version}")
