from __future__ import annotations
from enum import IntEnum, IntFlag
from typing import BinaryIO
from dataclasses import dataclass
import struct
import colorsys

HEADER_SIZE = 16

CONNECTION_ERRORS = (ConnectionResetError, BrokenPipeError, TimeoutError)


class ModeFlags(IntFlag):
    HAS_SPEED = (1 << 0)
    HAS_DIRECTION_LR = (1 << 1)
    HAS_DIRECTION_UD = (1 << 2)
    HAS_DIRECTION_HV = (1 << 3)
    HAS_BRIGHTNESS = (1 << 4)
    HAS_PER_LED_COLOR = (1 << 5)
    HAS_MODE_SPECIFIC_COLOR = (1 << 6)
    HAS_RANDOM_COLOR = (1 << 7)


class ModeDirections(IntEnum):
    LEFT = 0
    RIGHT = 1
    UP = 2
    DOWN = 3
    HORIZONTAL = 4
    VERTICAL = 5


class ModeColors(IntEnum):
    NONE = 0
    PER_LED = 1
    MODE_SPECIFIC = 2
    RANDOM = 3


class DeviceType(IntEnum):
    MOTHERBOARD = 0
    DRAM = 1
    GPU = 2
    COOLER = 3
    LEDSTRIP = 4
    KEYBOARD = 5
    MOUSE = 6
    MOUSEMAT = 7
    HEADSET = 8
    HEADSET_STAND = 9
    GAMEPAD = 10
    LIGHT = 11
    UNKNOWN = 12


class ZoneType(IntEnum):
    SINGLE = 0
    LINEAR = 1
    MATRIX = 2


class PacketType(IntEnum):
    REQUEST_CONTROLLER_COUNT = 0
    REQUEST_CONTROLLER_DATA = 1
    REQUEST_PROTOCOL_VERSION = 40
    SET_CLIENT_NAME = 50
    DEVICE_LIST_UPDATED = 100
    REQUEST_PROFILE_LIST = 150
    REQUEST_SAVE_PROFILE = 151
    REQUEST_LOAD_PROFILE = 152
    REQUEST_DELETE_PROFILE = 153
    RGBCONTROLLER_RESIZEZONE = 1000
    RGBCONTROLLER_UPDATELEDS = 1050
    RGBCONTROLLER_UPDATEZONELEDS = 1051
    RGBCONTROLLER_UPDATESINGLELED = 1052
    RGBCONTROLLER_SETCUSTOMMODE = 1100
    RGBCONTROLLER_UPDATEMODE = 1101


class OpenRGBDisconnected(ConnectionError):
    pass


def parse_string(data: bytes, start: int = 0) -> tuple[int, str]:
    '''
    Parses a string based on a size.

    :param data: the raw data to parse
    :param start: the location in the data to start parsing at
    :returns: the location in the data of the end of the string and the string itself
    '''
    size = struct.unpack('H', data[start:start + struct.calcsize('H')])[0]
    start += struct.calcsize("H")
    val = struct.unpack(f"{size}s", data[start:start + size])[0].decode()
    start += size
    return start, val.strip("\x00")


def pack_string(string: str) -> bytearray:
    '''
    Packs a string into bytes

    :param string: the string to pack
    :returns: bytes ready to be used
    '''
    num = len(string)
    return struct.pack(f"H{num}s", num + 1, string.encode('ascii')) + b'\x00'


def parse_list(kind: object, data: bytearray, version: int, start: int = 0) -> tuple[int, list]:
    '''
    Parses a list of objects and returns them

    :param kind: the class that the list consists of
    :param data: the raw data to parse
    :param start: the location in the data to start parsing
    '''
    num = struct.unpack("H", data[start:start + struct.calcsize("H")])[0]
    start += struct.calcsize("H")
    things = []
    for x in range(num):
        start, thing = kind.unpack(data, version, start, x)
        things.append(thing)
    return start, things


def pack_list(things: list, version: int) -> bytearray:
    '''
    Packs a list of things using the things' .pack() methods

    :param things: a list of things to pack
    :returns: bytes ready to be used
    '''
    return bytes(struct.pack("H", len(things))) + b''.join(thing.pack(version) for thing in things)


@dataclass
class RGBColor:
    red: int
    green: int
    blue: int

    def pack(self, version: int = 0) -> bytearray:
        '''
        Packs itself into a bytearray ready to be sent to the SDK or saved in a profile

        :returns: raw data ready to be sent or saved
        '''
        return struct.pack("BBBx", self.red, self.green, self.blue)

    @classmethod
    def unpack(cls, data: bytearray, version: int, start: int = 0, *args) -> tuple[int, RGBColor]:
        '''
        Unpacks an RGBColor object from bytes

        :returns: an RGBColor object
        '''
        size = struct.calcsize("BBBx")
        r, g, b = struct.unpack("BBBx", data[start:start + size])
        return (start + size), cls(r, g, b)

    @classmethod
    def fromHSV(cls, hue: int, saturation: int, value: int) -> RGBColor:
        '''
        Creates a RGBColor object from HSV values using colorsys
        '''
        return cls(*(round(i * 255) for i in colorsys.hsv_to_rgb(hue/360, saturation/100, value/100)))

    @classmethod
    def fromHEX(cls, hex: str) -> RGBColor:
        '''
        Creates a RGBColor object from a hex color string
        '''
        return cls(*(int(hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)))


@dataclass
class LEDData:
    name: str
    value: int

    def pack(self, version: int) -> bytearray:
        '''
        Packs itself into a bytearray ready to be sent to the SDK or saved in a profile

        :returns: raw data ready to be sent or saved
        '''
        return (
            pack_string(self.name)
            + struct.pack("I", self.value)
        )

    @classmethod
    def unpack(cls, data: bytearray, version: int, start: int = 0, *args) -> tuple[int, LEDData]:
        '''
        Creates a new LEDData object from raw bytes

        :param data: the raw bytes from the SDK
        :param start: what place in the data object to start
        '''
        start, name = parse_string(data, start)
        value = struct.unpack("I", data[start:start + struct.calcsize("I")])[0]
        start += struct.calcsize("I")
        return start, cls(name, value)


@dataclass
class ModeData:
    id: int
    name: str
    value: int
    flags: ModeFlags
    speed_min: int
    speed_max: int
    colors_min: int
    colors_max: int
    speed: int
    direction: ModeDirections
    color_mode: ModeColors
    colors: list[RGBColor]

    def validate(self):
        '''
        Tests the values of the mode data and raises a `ValueError` if the validation fails
        '''
        try:
            if ModeFlags.HAS_SPEED in self.flags:
                assert self.speed is not None
                assert self.speed_min <= self.speed <= self.speed_max or self.speed_max <= self.speed <= self.speed_min
            if ModeFlags.HAS_MODE_SPECIFIC_COLOR in self.flags:
                assert self.colors_min <= len(self.colors) <= self.colors_max
        except AssertionError as e:
            raise ValueError("Mode validation failed.  Required values invalid or not present") from e

        try:
            if ModeFlags.HAS_SPEED not in self.flags:
                assert all((i is None for i in (self.speed_max, self.speed_min, self.speed)))
            if ModeFlags.HAS_MODE_SPECIFIC_COLOR not in self.flags:
                assert all((i is None for i in (self.colors_max, self.colors_min, self.colors)))
        except AssertionError as e:
            raise ValueError("Mode validation failed.  Values are set that are not supported by this mode") from e

    def pack(self, version: int) -> bytearray:
        '''
        Packs itself into a bytearray ready to be sent to the SDK or saved in a profile

        :returns: raw data ready to be sent or saved
        '''
        self.validate()
        data = (
            struct.pack("i", self.id)
            + pack_string(self.name)
            + struct.pack(
                f"=i8I",
                self.value,
                self.flags,
                self.speed_min if self.speed_min is not None else 0,
                self.speed_max if self.speed_max is not None else 0,
                self.colors_min if self.colors_min is not None else 0,
                self.colors_max if self.colors_max is not None else 0,
                self.speed if self.speed is not None else 0,
                self.direction if self.direction is not None else 0,
                self.color_mode
            )
        )
        data += pack_list(self.colors if self.colors is not None else [], version)
        data = struct.pack("I", len(data) + struct.calcsize("I")) + data
        return data

    @classmethod
    def unpack(cls, data: bytearray, version: int, start: int = 0, index: int = 0) -> tuple[int, ModeData]:
        '''
        Creates a new ModeData object from raw bytes

        :param data: the raw bytes from the SDK
        :param start: what place in the data object to start
        :param index: which mode this is
        '''
        start, val = parse_string(data, start)
        buff = list(struct.unpack("i8IH", data[start:start + struct.calcsize("i8IH")]))
        start += struct.calcsize("i8IH")
        colors = []
        buff[1] = ModeFlags(buff[1])

        # Garbage data will be sent if these flags aren't set
        if (ModeFlags.HAS_DIRECTION_HV in buff[1]
                or ModeFlags.HAS_DIRECTION_UD in buff[1]
                or ModeFlags.HAS_DIRECTION_LR in buff[1]):
            buff[7] = ModeDirections(buff[7])
        else:
            buff[7] = None
        if ModeFlags.HAS_SPEED not in buff[1]:
            buff[2], buff[3], buff[6] = None, None, None
        buff[8] = ModeColors(buff[8])
        for i in range(buff[-1]):
            start, color = RGBColor.unpack(data, version, start)
            colors.append(color)
        if buff[-1] == 0:
            colors, buff[4], buff[5] = None, None, None
        return start, cls(index, val, *buff[:9], colors)


@dataclass
class ZoneData:
    name: str
    zone_type: ZoneType
    leds_min: int
    leds_max: int
    num_leds: int
    mat_height: int
    mat_width: int
    matrix_map: list[list] = None
    leds: list[LEDData] = None
    colors: list[RGBColor] = None
    start_idx: int = None

    def pack(self, version: int) -> bytearray:
        '''
        Packs itself into a bytearray ready to be sent to the SDK or saved in a profile

        :returns: raw data ready to be sent or saved
        '''
        data = (
            pack_string(self.name)
            + struct.pack(
                "i3I",
                self.zone_type,
                self.leds_min,
                self.leds_max,
                self.num_leds
            )
        )
        if self.mat_height > 0 and self.mat_width > 0:
            flat = [i for li in self.matrix_map for i in li]
            assert len(flat) == (self.mat_width * self.mat_height)
            data += struct.pack(
                f"HII{len(flat)}I",
                len(flat),
                self.mat_height,
                self.mat_width,
                *flat
            )
        else:
            data += struct.pack("H", 0)
        return data

    @classmethod
    def unpack(cls, data: bytearray, version: int, start: int = 0, *args) -> tuple[int, ZoneData]:
        '''
        Unpacks the raw data into a ZoneData object

        :param data: The raw byte data to unpack
        :param start: What place in the data object to start
        '''
        start, name = parse_string(data, start)
        buff = list(struct.unpack("iIIIH", data[start:start + struct.calcsize("iIIIH")]))
        start += struct.calcsize("iIIIH")
        height, width = 0, 0
        matrix = [[]]
        if buff[0] == ZoneType.MATRIX:
            height, width = struct.unpack("II", data[start:start + struct.calcsize("II")])
            start += struct.calcsize("II")
            matrix = [[] for x in range(height)]
            for y in range(height):
                matrix[y] = list(struct.unpack(f"{width}I", data[start:start + struct.calcsize("I")*width]))
                start += struct.calcsize("I")*width
            for idx, row in enumerate(matrix):
                matrix[idx] = [x if x != 0xFFFFFFFF else None for x in row]
        return start, cls(name, ZoneType(buff[0]), *buff[1:-1], height, width, matrix)


@dataclass
class MetaData:
    vendor: str
    description: str
    version: str
    serial: str
    location: str

    def pack(self, version: int) -> bytearray:
        '''
        Packs itself into a bytearray ready to be sent to the SDK or saved in a profile

        :returns: raw data ready to be sent or saved
        '''
        buff = (
            pack_string(self.description)
            + pack_string(self.version)
            + pack_string(self.serial)
            + pack_string(self.location)
        )
        if version >= 1:
            buff = pack_string(self.vendor) + buff
        return buff

    @classmethod
    def unpack(cls, data: bytearray, version: int, start: int = 0, *args) -> tuple[int, MetaData]:
        '''
        Unpacks the raw data into a MetaData object

        :param data: The raw byte data to unpack
        :param start: What place in the data object to start
        '''
        buff = []
        for x in range(5 if version >= 1 else 4):
            start, val = parse_string(data, start)
            buff.append(val)
        if version < 1:
            buff = [None] + buff
        return start, cls(*buff)


@dataclass
class ControllerData:
    name: str
    metadata: MetaData
    device_type: DeviceType
    leds: list[LEDData]
    zones: list[ZoneData]
    modes: list[ModeData]
    colors: list[RGBColor]
    active_mode: int

    def pack(self, version: int) -> bytearray:
        '''
        Packs itself into a bytearray ready to be sent to the SDK or saved in a profile

        :returns: raw data ready to be sent or saved
        '''
        buff = (
            struct.pack("i", self.device_type)
            + pack_string(self.name)
            + self.metadata.pack(version)
            + struct.pack("H", len(self.modes))
            + struct.pack("i", self.active_mode)
            + b''.join(mode.pack(version)[struct.calcsize("Ii"):] for mode in self.modes)
            + pack_list(self.zones, version)
            + pack_list(self.leds, version)
            + pack_list(self.colors, version)
        )
        buff = struct.pack("I", len(buff) + struct.calcsize("I")) + buff
        return buff

    @classmethod
    def unpack(cls, data: bytearray, version: int, start: int = 0) -> ControllerData:
        '''
        Unpacks the raw bytes received from the SDK into a ControllerData dataclass

        :param data: The raw data from a response to a request for device data
        :returns: A ControllerData dataclass ready to pass into the OpenRGBClient's calback function
        '''
        buff = struct.unpack("Ii", data[start:start + struct.calcsize("Ii")])
        start += struct.calcsize("Ii")
        try:
            device_type = DeviceType(buff[1])
        except ValueError:
            device_type = DeviceType.UNKNOWN
        start, name = parse_string(data, start)
        start, metadata = MetaData.unpack(data, version, start)
        buff = struct.unpack("=Hi", data[start:start + struct.calcsize("=Hi")])
        start += struct.calcsize("=Hi")
        num_modes = buff[0]
        active_mode = buff[-1]
        modes = []
        for x in range(num_modes):
            start, mode = ModeData.unpack(data, version, start, x)
            modes.append(mode)
        start, zones = parse_list(ZoneData, data, version, start)
        start, leds = parse_list(LEDData, data, version, start)
        start, colors = parse_list(RGBColor, data, version, start)
        i = 0
        for zone in zones:
            zone.start_idx = i
            zone.leds = leds[i:i + zone.num_leds]
            zone.colors = colors[i:i + zone.num_leds]
            i += zone.num_leds
        # print("Device Information:\n", "\tDevice type:", device_type, "\n\t", end="")
        # print(metadata, sep="\n\t")
        # print("Mode Information:\n", "\tNumber of modes:", len(modes), "\n\tActive Mode:", active_mode, "\n\t", end="")
        # print(*modes, sep='\n\t')
        # print("Zone Information:\n", "\tNumber of zones:", len(zones), "\n\t", end="")
        # print(*zones, sep='\n\t')
        # print("LED Information:\n", "\tNumber of LEDs:", len(leds), "\n\t", end="")
        # print(*leds, sep="\n\t")
        # print("Color Information:\n", "\tNumber of Colors:", len(colors), "\n\t", end="")
        # print(*colors, sep="\n\t")
        # print("---------------------------------")
        return cls(
            name,
            metadata,
            device_type,
            leds,
            zones,
            modes,
            colors,
            active_mode
        )


@dataclass
class LocalProfile:
    '''
    A dataclass to load, store, and pack the data found in an OpenRGB profile file.
    '''
    controllers: list[ControllerData]

    def pack(self) -> bytearray:
        data = bytearray()
        data += struct.pack("16sI", b'OPENRGB_PROFILE\x00', 1)
        for dev in self.controllers:
            data += dev.pack(0)
        return data

    @classmethod
    def unpack(cls, profile: BinaryIO) -> LocalProfile:
        header = profile.read(16 + struct.calcsize("I"))
        if struct.unpack("16s", header[:16])[0] != b"OPENRGB_PROFILE\x00":
            raise ValueError("The file is not an OpenRGB profile")
        version = struct.unpack("I", header[16:])[0]
        if version == 1:
            controllers = []
            while True:
                d = profile.read(struct.calcsize("I"))
                if len(d) < struct.calcsize("I"):
                    break
                size = struct.unpack("I", d)[0]
                profile.seek(profile.tell() - struct.calcsize("I"))
                new_data = ControllerData.unpack(profile.read(size), 0)
                controllers.append(new_data)
            return cls(controllers)


@dataclass
class Profile:
    '''
    A simple dataclass to parse profiles from the server.
    '''
    name: str

    def pack(self) -> bytearray:
        return bytearray(f"{self.name}\0", 'utf-8')

    @classmethod
    def unpack(cls, data: bytearray, version: int, start: int = 0, *args) -> Profile:
        x, s = parse_string(data, start)
        return x, cls(s)

class RGBObject:
    '''
    A parent class that includes a few generic functions that use the
    implementation provided by the children.
    '''

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name}, id={self.id})"

    def set_color(self, color: RGBColor, start: int = 0, end: int = 0, fast: bool = False):
        '''
        Sets the color

        :param color: the color to set
        '''
        pass

    def clear(self):
        '''
        Turns all of the LEDS off
        '''
        self.set_color(RGBColor(0, 0, 0))

    def off(self):
        '''
        Same as RGBContainer.clear
        '''
        self.clear()

    def update(self):
        '''
        Gets the current status from the SDK server, ensuring a correct
        internal state.
        '''
        self.comms.requestDeviceData(self.device_id)


class RGBContainer(RGBObject):
    '''
    A parent class for RGBObjects that can control more than one LED like the
    :any:`Device` class or the :any:`Zone` class.
    '''

    def set_colors(self, colors: list[RGBColor], start: int = 0, end: int = 0, fast: bool = False):
        '''
        Sets mutliple colors

        :param colors: A list of colors to set
        '''
        pass

    def show(self, fast: bool = False, force: bool = False):
        '''
        Applies changes in the color attribute
        '''
        if len(self.colors) > len(self._colors):
            raise ValueError(f"`self.colors` is longer than expected length `{len(self._colors)}`")
        elif len(self.colors) < len(self._colors):
            raise ValueError(f"`self.colors` is shorter than expected length `{len(self._colors)}`")
        changed = [(i, color) for i, color in enumerate(self.colors) if color != self._colors[i]]
        if force:
            self.set_colors(self.colors, fast=True)
        elif len(changed) == 0:
            return
        elif len(changed) == 1:
            self.leds[changed[0][0]].set_color(changed[0][1], fast=True)
        elif len(changed) > 1:
            start, end = changed[0][0], changed[-1][0] + 1
            colors = self.colors[start:end]
            self.set_colors(colors, start, end, fast=True)
        self._colors = self.colors[:]
        if not fast:
            self.update()
