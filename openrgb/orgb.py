from __future__ import annotations
import struct
from openrgb import utils
from typing import Union, Optional
from openrgb.network import NetworkClient
# from dataclasses import dataclass
from time import sleep
from os import environ


class LED(utils.RGBObject):
    '''
    A class to represent individual LEDs
    '''

    def __init__(self, data: utils.LEDData, color: utils.RGBColor, led_id: int, device_id: int, network_client: NetworkClient):
        self.id = led_id
        self.device_id = device_id
        self.comms = network_client
        self._update(data, color)

    def _update(self, data: utils.LEDData, color: utils.RGBColor):
        self.name = data.name
        self.colors = [color]
        self._colors = self.colors[:]

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
        self.leds = [None for led in data.leds]
        self.device_id = device_id
        self.comms = network_client
        self.id = zone_id
        self._update(data)

    def _update(self, data: utils.ZoneData):
        self.name = data.name
        self.type = data.zone_type
        if len(self.leds) != len(data.leds):
            self.leds = [None for led in data.leds]
        for x in range(len(data.leds)):
            if self.leds[x] is None:
                self.leds[x] = LED(data.leds[x], data.colors[x], x, self.device_id, self.comms)
            else:
                self.leds[x]._update(data.leds[x], data.colors[x])
        self.mat_width = data.mat_width
        self.mat_height = data.mat_height
        self.matrix_map = data.matrix_map
        self.colors = data.colors
        self._colors = self.colors[:]

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

    def set_colors(self, colors: list[utils.RGBColor], start: int = 0, end: int = 0, fast: bool = False):
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
        self.leds = [None for i in data.leds]
        self.zones = [None for i in data.zones]
        self.id = device_id
        self.device_id = device_id
        self.comms = network_client
        self._update(data)

    def _update(self, data: utils.ControllerData):
        self.name = data.name
        self.metadata = data.metadata
        self.type = data.device_type
        if len(self.leds) != len(data.leds):
            self.leds = [None for i in data.leds]
        for x in range(len(data.leds)):
            if self.leds[x] is None:
                self.leds[x] = LED(data.leds[x], data.colors[x], x, self.device_id, self.comms)
            else:
                self.leds[x]._update(data.leds[x], data.colors[x])
        for x in range(len(data.zones)):
            if self.zones[x] is None:
                self.zones[x] = Zone(data.zones[x], x, self.device_id, self.comms)
            else:
                self.zones[x]._update(data.zones[x])
        self.modes = data.modes
        self.colors = data.colors
        self._colors = self.colors[:]
        self.active_mode = data.active_mode
        self.data = data

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

    def set_colors(self, colors: list[utils.RGBColor], start: int = 0, end: int = 0, fast: bool = False):
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
            try:
                mode = next((m for m in self.modes if m.name.lower() == mode.lower()))
            except StopIteration as e:
                raise ValueError(f"Mode `{mode}` not found for device `{self.name}`") from e
        data = mode.pack(self.comms._protocol_version)
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
        self.profiles = []
        self.comms = NetworkClient(self._callback, address, port, name, protocol_version)
        self.address = address
        self.port = port
        self.name = name
        self.comms.requestDeviceNum()
        while any((dev is None for dev in self.devices)):
            sleep(.1)
        self.update_profiles()

    def __repr__(self):
        return f"OpenRGBClient(address={self.address}, port={self.port}, name={self.name})"

    def _callback(self, device: int, type: int, data: Optional):
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
                    self.devices[device]._update(data)
            except IndexError:
                self.comms.requestDeviceNum()
        elif type == utils.PacketType.DEVICE_LIST_UPDATED:
            self.device_num = 0
            self.comms.requestDeviceNum()
        elif type == utils.PacketType.REQUEST_PROFILE_LIST:
            self.profiles = data

    def set_color(self, color: utils.RGBColor, fast: bool = False):
        '''
        Sets the color of every device.

        :param color: the color to set the devices to
        :param fast: If you care more about quickly setting colors than having correct internal state data, then set :code:`fast` to :code:`True`
        '''
        for device in self.devices:
            device.set_color(color, fast=fast)

    def get_devices_by_type(self, type: utils.DeviceType) -> list[Device]:
        '''
        Gets a list of devices that are the same type as requested

        :param type: what type of device you want to get
        '''
        return [device for device in self.devices if device.type == type]

    def get_devices_by_name(self, name: str, exact: bool = True) -> list[Device]:
        '''
        Gets a list of any devices matching the requested name

        :param name: the name of the device(s) you want to get
        :param exact: whether to check for only a precise match or accpet a device that contains name
        '''
        if exact:
            return [device for device in self.devices if device.name == name]
        return [device for device in self.devices if name.lower() in device.name.lower()]

    def load_profile(self, name: Union[str, int, utils.Profile], local: bool = False, directory: str = ''):
        '''
        Loads an OpenRGB profile

        :param name: Can be a profile's name, index, or even the Profile itself
        :param local: Whether to load a local file or a profile from the server.
        :param directory: what directory the profile is in.  Defaults to HOME/.config/OpenRGB
        '''
        if local:
            assert type(name) is str
            if directory == '':
                directory = environ['HOME'].rstrip("/") + "/.config/OpenRGB"
            with open(f'{directory}/{name}.orp', 'rb') as f:
                controllers = utils.LocalProfile.unpack(f).controllers
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
        else:
            if type(name) is str:
                try:
                    name = next(p for p in self.profiles if p.name.lower() == name.lower())
                except StopIteration as e:
                    raise ValueError(f"`{name}` is not an existing profile") from e
            elif type(name) is int:
                name = self.profiles[name]
            elif type(name) is utils.Profile:
                pass
            name = name.pack()
            self.comms.send_header(0, utils.PacketType.REQUEST_LOAD_PROFILE, len(name))
            self.comms.send_data(name)

    def save_profile(self, name: Union[str, int, utils.Profile], local: bool = False, directory: str = ''):
        '''
        Saves the current state of all of your devices to a new or existing
        OpenRGB profile

        :param name: Can be a profile's name, index, or even the Profile itself
        :param local: Whether to load a local file or a profile on the server.
        :param directory: what directory to save the profile in.  Defaults to HOME/.config/OpenRGB
        '''
        if local:
            self.update()
            if directory == '':
                directory = environ['HOME'].rstrip("/") + "/.config/OpenRGB"
            with open(f'{directory.rstrip("/")}/{name}.orp', 'wb') as f:
                f.write(utils.Profile([dev.data for dev in self.devices]).pack())
        else:
            if type(name) is str:
                try:
                    name = next(p for p in self.profiles if p.name.lower() == name.lower())
                except StopIteration:
                    name = utils.Profile(name)
            elif type(name) is int:
                name = self.profiles[name]
            elif type(name) is utils.Profile:
                pass
            name = name.pack()
            self.comms.send_header(0, utils.PacketType.REQUEST_SAVE_PROFILE, len(name))
            self.comms.send_data(name)
            self.update_profiles()

    def delete_profile(self, name: Union[str, int, utils.Profile]):
        '''
        Deletes the selected profile

        :param name: Can be a profile's name, index, or even the Profile itself
        '''
        if type(name) is str:
            try:
                name = next(p for p in self.profiles if p.name.lower() == name.lower())
            except StopIteration as e:
                raise ValueError(f"`{name}` is not an existing profile") from e
        elif type(name) is int:
            name = self.profiles[name]
        elif type(name) is utils.Profile:
            pass
        name = name.pack()
        self.comms.send_header(0, utils.PacketType.REQUEST_DELETE_PROFILE, len(name))
        self.comms.send_data(name)
        self.update_profiles()

    def update(self):
        '''
        Gets the current state of your devices from the SDK server, which is
        useful if you change something from the gui or another SDK client and
        need to sync up the changes.
        '''
        self.comms.requestDeviceNum()
        for x in range(self.device_num):
            self.comms.requestDeviceData(x)

    def update_profiles(self):
        '''
        Gets the list of available profiles from the server.
        '''
        self.comms.requestProfileList()

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
        return self.comms._protocol_version

    @protocol_version.setter
    def protocol_version(self, version: int):
        '''Sets the procol version of the connected SDK server'''
        if version <= self.comms.max_protocol_version:
            self.comms._protocol_version = version
        else:
            raise ValueError(f"version {version} is greater than maximum supported version {self.comms.max_protocol_version}")

    @property
    def ee_devices(self):
        '''
        A subset of the device list that only includes devices with a direct
        control mode.  These devices are suitable to use with an effects engine.
        '''
        return [dev for dev in self.devices for mode in dev.modes if mode.name.lower() == 'direct']
