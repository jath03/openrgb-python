from __future__ import annotations
from enum import IntEnum, IntFlag
from typing import BinaryIO, Any, Iterator, Optional
from dataclasses import dataclass, field
import struct
import colorsys
import socket

HEADER_SIZE = 16

CONNECTION_ERRORS = (ConnectionResetError, BrokenPipeError, TimeoutError, socket.timeout)
PARSING_ERRORS = (UnicodeError, struct.error)


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
    SPEAKER = 12
    VIRTUAL = 13
    UNKNOWN = 14


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
    RGBCONTROLLER_SAVEMODE = 1102


class OpenRGBDisconnected(ConnectionError):
    pass


class SDKVersionError(NotImplementedError):
    pass


class ControllerParsingError(ValueError):
    pass


def parse_var(type: str, data: Iterator[int]) -> Any:
    size = struct.calcsize(type)
    d = []
    for _ in range(size):
        d.append(int(next(data)))
    try:
        return struct.unpack(type, bytes(d))[0]
    except IndexError:
        return


def parse_string(data: Iterator[int]) -> str:
    '''
    Parses a string based on a size.

    :param data: the raw data to parse
    :returns: A parsed string
    '''
    length = parse_var('H', data)
    return parse_var(f'{length}s', data).decode().rstrip('\x00')


def pack_string(string: str) -> bytes:
    '''
    Packs a string into bytes

    :param string: the string to pack
    :returns: bytes ready to be used
    '''
    num = len(string)
    return struct.pack(f"H{num}s", num + 1, string.encode('ascii')) + b'\x00'


def parse_list(kind: object, data: Iterator[int], version: int) -> list:
    '''
    Parses a list of objects and returns them

    :param kind: the class that the list consists of
    :param data: the raw data to parse
    :param start: the location in the data to start parsing
    '''
    length = parse_var('H', data)
    things = []
    for x in range(length):
        things.append(kind.unpack(data, version, x))  # type: ignore
    return things


def pack_list(things: list, version: int) -> bytes:
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

    def pack(self, version: int = 0) -> bytes:
        '''
        Packs itself into a bytes ready to be sent to the SDK or saved in a profile

        :returns: raw data ready to be sent or saved
        '''
        return struct.pack("BBBx", self.red, self.green, self.blue)

    @classmethod
    def unpack(cls, data: Iterator[int], version: int, *args) -> RGBColor:
        '''
        Unpacks an RGBColor object from bytes

        :returns: an RGBColor object
        '''
        r = parse_var('B', data)
        g = parse_var('B', data)
        b = parse_var('B', data)
        parse_var('x', data)
        return cls(r, g, b)

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

    def pack(self, version: int) -> bytes:
        '''
        Packs itself into a bytes ready to be sent to the SDK or saved in a profile

        :returns: raw data ready to be sent or saved
        '''
        return (
            pack_string(self.name)
            + struct.pack("I", self.value)
        )

    @classmethod
    def unpack(cls, data: Iterator[int], version: int, *args) -> LEDData:
        '''
        Creates a new LEDData object from raw bytes

        :param data: the raw bytes from the SDK
        :param start: what place in the data object to start
        '''
        name = parse_string(data)
        value = parse_var('I', data)
        return cls(name, value)


@dataclass
class ModeData:
    id: int
    name: str
    value: int
    flags: ModeFlags
    speed_min: Optional[int]
    speed_max: Optional[int]
    brightness_min: Optional[int]
    brightness_max: Optional[int]
    colors_min: Optional[int]
    colors_max: Optional[int]

    speed: Optional[int]
    brightness: Optional[int]
    direction: Optional[ModeDirections]
    color_mode: ModeColors
    colors: Optional[list[RGBColor]]

    def validate(self, version: int):
        '''
        Tests the values of the mode data and raises a `ValueError` if the validation fails
        '''
        try:
            if ModeFlags.HAS_SPEED in self.flags:
                assert self.speed is not None
                assert self.speed_min <= self.speed <= self.speed_max or self.speed_max <= self.speed <= self.speed_min  # type: ignore
            if ModeFlags.HAS_MODE_SPECIFIC_COLOR in self.flags:
                assert self.colors_min <= len(self.colors) <= self.colors_max  # type: ignore
            if ModeFlags.HAS_BRIGHTNESS in self.flags and version >= 3:
                assert self.brightness_min <= self.brightness <= self.brightness_max  # type: ignore
        except AssertionError as e:
            raise ValueError("Mode validation failed.  Required values invalid or not present") from e

        try:
            if ModeFlags.HAS_SPEED not in self.flags:
                assert all((i is None for i in (self.speed_max, self.speed_min, self.speed)))
            if ModeFlags.HAS_MODE_SPECIFIC_COLOR not in self.flags:
                assert all((i is None for i in (self.colors_max, self.colors_min, self.colors)))
            if ModeFlags.HAS_BRIGHTNESS not in self.flags or version < 3:
                assert all((i is None for i in (self.brightness_max, self.brightness_min, self.brightness)))
        except AssertionError as e:
            raise ValueError("Mode validation failed.  Values are set that are not supported by this mode") from e

    def pack(self, version: int) -> bytes:
        '''
        Packs itself into a bytes ready to be sent to the SDK or saved in a profile

        :returns: raw data ready to be sent or saved
        '''
        self.validate(version)
        data = struct.pack("i", self.id)
        data += pack_string(self.name)
        data += struct.pack('i', self.value)
        data += struct.pack('I', self.flags)
        data += struct.pack('I', self.speed_min if self.speed_min is not None else 0)
        data += struct.pack('I', self.speed_max if self.speed_max is not None else 0)
        if version >= 3:
            data += struct.pack('I', self.brightness_min if self.brightness_min is not None else 0)
            data += struct.pack('I', self.brightness_max if self.brightness_max is not None else 0)
        data += struct.pack('I', self.colors_min if self.colors_min is not None else 0)
        data += struct.pack('I', self.colors_max if self.colors_max is not None else 0)
        data += struct.pack('I', self.speed if self.speed is not None else 0)
        if version >= 3:
            data += struct.pack('I', self.brightness if self.brightness is not None else 0)
        data += struct.pack('I', self.direction if self.direction is not None else 0)
        data += struct.pack('I', self.color_mode)

        data += pack_list(self.colors if self.colors is not None else [], version)
        data = struct.pack("I", len(data) + struct.calcsize("I")) + data
        return data

    @classmethod
    def unpack(cls, data: Iterator[int], version: int, index: int = 0) -> ModeData:
        '''
        Creates a new ModeData object from raw bytes

        :param data: the raw bytes from the SDK
        :param start: what place in the data object to start
        :param index: which mode this is
        '''
        name = parse_string(data)
        value = parse_var('i', data)
        flags = ModeFlags(parse_var('I', data))
        speed_min = parse_var('I', data)
        speed_max = parse_var('I', data)
        if version >= 3:
            brightness_min = parse_var('I', data)
            brightness_max = parse_var('I', data)
        else:
            brightness_min = None
            brightness_max = None
        colors_min = parse_var('I', data)
        colors_max = parse_var('I', data)

        speed = parse_var('I', data)
        if version >= 3:
            brightness = parse_var('I', data)
        else:
            brightness = None
        direction = parse_var('I', data)
        color_mode = ModeColors(parse_var('I', data))
        num_colors = parse_var('H', data)

        colors = []

        # Garbage data will be sent if these flags aren't set
        if (ModeFlags.HAS_DIRECTION_HV in flags
                or ModeFlags.HAS_DIRECTION_UD in flags
                or ModeFlags.HAS_DIRECTION_LR in flags):
            direction = ModeDirections(direction)
        else:
            direction = None
        if ModeFlags.HAS_SPEED not in flags:
            speed_min, speed_max, speed = None, None, None
        if ModeFlags.HAS_BRIGHTNESS not in flags or version < 3:
            brightness_min, brightness_max, brightness = None, None, None

        for i in range(num_colors):
            color = RGBColor.unpack(data, version)
            colors.append(color)
        if num_colors == 0:
            colors, colors_min, colors_max = None, None, None  # type: ignore

        return cls(
            index,
            name,
            value,
            flags,
            speed_min,
            speed_max,
            brightness_min,
            brightness_max,
            colors_min,
            colors_max,
            speed,
            brightness,
            direction,
            color_mode,
            colors
        )


@dataclass
class ZoneData:
    name: str
    zone_type: ZoneType
    leds_min: int
    leds_max: int
    num_leds: int
    mat_height: Optional[int]
    mat_width: Optional[int]
    matrix_map: Optional[list[list[Optional[int]]]] = None
    leds: list[LEDData] = field(default_factory=list)
    colors: list[RGBColor] = field(default_factory=list)
    start_idx: int = 0

    def pack(self, version: int) -> bytes:
        '''
        Packs itself into a bytes ready to be sent to the SDK or saved in a profile

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
        if self.mat_height > 0 and self.mat_width > 0:  # type: ignore
            flat = [i for li in self.matrix_map for i in li]  # type: ignore
            assert len(flat) == (self.mat_width * self.mat_height)  # type: ignore
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
    def unpack(cls, data: Iterator[int], version: int, *args) -> ZoneData:
        '''
        Unpacks the raw data into a ZoneData object

        :param data: The raw byte data to unpack
        :param start: What place in the data object to start
        '''
        name = parse_string(data)
        zone_type = ZoneType(parse_var('i', data))
        leds_min = parse_var('I', data)
        leds_max = parse_var('I', data)
        num_leds = parse_var('I', data)
        matrix_zone_size = parse_var('H', data)
        if zone_type == ZoneType.MATRIX:
            height = parse_var('I', data)
            width = parse_var('I', data)
            matrix: list[list[Optional[int]]] = [[] for x in range(height)]
            for y in range(height):
                for _ in range(width):
                    matrix[y].append(parse_var('I', data))
            for idx, row in enumerate(matrix):
                matrix[idx] = [x if x != 0xFFFFFFFF else None for x in row]
        else:
            height, width = None, None
            matrix = None  # type: ignore
        return cls(
            name,
            zone_type,
            leds_min,
            leds_max,
            num_leds,
            height,
            width,
            matrix
        )


@dataclass
class MetaData:
    vendor: Optional[str]
    description: str
    version: str
    serial: str
    location: str

    def pack(self, version: int) -> bytes:
        '''
        Packs itself into a bytes ready to be sent to the SDK or saved in a profile

        :returns: raw data ready to be sent or saved
        '''
        buff = (
            pack_string(self.description)
            + pack_string(self.version)
            + pack_string(self.serial)
            + pack_string(self.location)
        )
        if version >= 1:
            buff = pack_string(self.vendor) + buff  # type: ignore
        return buff

    @classmethod
    def unpack(cls, data: Iterator[int], version: int, *args) -> MetaData:
        '''
        Unpacks the raw data into a MetaData object

        :param data: The raw byte data to unpack
        :param start: What place in the data object to start
        '''
        if version >= 1:
            vendor: Optional[str] = parse_string(data)
        else:
            vendor = None
        description = parse_string(data)
        fw_version = parse_string(data)
        serial = parse_string(data)
        location = parse_string(data)

        return cls(
            vendor,
            description,
            fw_version,
            serial,
            location
        )


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

    def pack(self, version: int) -> bytes:
        '''
        Packs itself into a bytes ready to be sent to the SDK or saved in a profile

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
    def unpack(cls, raw_data: bytes, version: int, start: int = 0) -> ControllerData:
        '''
        Unpacks the raw bytes received from the SDK into a ControllerData dataclass

        :param data: The raw data from a response to a request for device data
        :returns: A ControllerData dataclass ready to pass into the OpenRGBClient's calback function
        '''
        data = iter(raw_data)
        size = parse_var('I', data)
        try:
            device_type = DeviceType(parse_var('i', data))
        except ValueError:
            device_type = DeviceType.UNKNOWN
        name = parse_string(data)
        metadata = MetaData.unpack(data, version)
        num_modes = parse_var('H', data)
        active_mode = parse_var('i', data)
        modes = []
        for x in range(num_modes):
            mode = ModeData.unpack(data, version, x)
            modes.append(mode)
        zones = parse_list(ZoneData, data, version)
        leds = parse_list(LEDData, data, version)
        colors = parse_list(RGBColor, data, version)
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

    def pack(self) -> bytes:
        data = bytes()
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
            version = 0
        controllers = []
        while True:
            d = profile.read(struct.calcsize("I"))
            if len(d) < struct.calcsize("I"):
                break
            size = struct.unpack("I", d)[0]
            profile.seek(profile.tell() - struct.calcsize("I"))
            new_data = ControllerData.unpack(profile.read(size), version)
            controllers.append(new_data)
        return cls(controllers)


@dataclass
class Profile:
    '''
    A simple dataclass to parse profiles from the server.
    '''
    name: str

    def pack(self) -> bytes:
        return bytes(f"{self.name}\0", 'utf-8')

    @classmethod
    def unpack(cls, data: Iterator[int], version: int, *args) -> Profile:
        s = parse_string(data)
        return cls(s)


class RGBObject:
    '''
    A parent class that includes a few generic functions that use the
    implementation provided by the children.
    '''

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name}, id={self.id})"

    def set_color(self, color: RGBColor, fast: bool = False):
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

    def __init__(self):
        self.colors: list[RGBColor] = []
        self._colors: list[RGBColor] = []
        self.leds: list = []

    def set_colors(self, colors: list[RGBColor], fast: bool = False):
        '''
        Sets mutliple colors

        :param colors: A list of colors to set
        '''
        pass

    def show(self, fast: bool = False, force: bool = False):
        '''
        Applies changes in the color attribute

        :param fast: Whether or not update the device on each call
        :param force: If True, the function will update every led, regardless of previous state.
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
            self.set_colors(self.colors, fast=True)
        self._colors = self.colors[:]
        if not fast:
            self.update()
