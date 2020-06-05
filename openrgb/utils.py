from enum import IntEnum, IntFlag
from typing import List, TypeVar, Type, Tuple
from dataclasses import dataclass
import struct
import colorsys

HEADER_SIZE = 16


class ModeFlags(IntFlag):
    MODE_FLAG_HAS_SPEED = (1 << 0)
    MODE_FLAG_HAS_DIRECTION_LR = (1 << 1)
    MODE_FLAG_HAS_DIRECTION_UD = (1 << 2)
    MODE_FLAG_HAS_DIRECTION_HV = (1 << 3)
    MODE_FLAG_HAS_BRIGHTNESS = (1 << 4)
    MODE_FLAG_HAS_PER_LED_COLOR = (1 << 5)
    MODE_FLAG_HAS_MODE_SPECIFIC_COLOR = (1 << 6)
    MODE_FLAG_HAS_RANDOM_COLOR = (1 << 7)


class ModeDirections(IntEnum):
    MODE_DIRECTION_LEFT = 0
    MODE_DIRECTION_RIGHT = 1
    MODE_DIRECTION_UP = 2
    MODE_DIRECTION_DOWN = 3
    MODE_DIRECTION_HORIZONTAL = 4
    MODE_DIRECTION_VERTICAL = 5


class ModeColors(IntEnum):
    MODE_COLORS_NONE = 0
    MODE_COLORS_PER_LED = 1
    MODE_COLORS_MODE_SPECIFIC = 2
    MODE_COLORS_RANDOM = 3


class DeviceType(IntEnum):
    DEVICE_TYPE_MOTHERBOARD = 0
    DEVICE_TYPE_DRAM = 1
    DEVICE_TYPE_GPU = 2
    DEVICE_TYPE_COOLER = 3
    DEVICE_TYPE_LEDSTRIP = 4
    DEVICE_TYPE_KEYBOARD = 5
    DEVICE_TYPE_MOUSE = 6
    DEVICE_TYPE_MOUSEMAT = 7
    DEVICE_TYPE_HEADSET = 8
    DEVICE_TYPE_UNKNOWN = 9


class ZoneType(IntEnum):
    ZONE_TYPE_SINGLE = 0
    ZONE_TYPE_LINEAR = 1
    ZONE_TYPE_MATRIX = 2


class PacketType(IntEnum):
    NET_PACKET_ID_REQUEST_CONTROLLER_COUNT = 0
    NET_PACKET_ID_REQUEST_CONTROLLER_DATA = 1
    NET_PACKET_ID_SET_CLIENT_NAME = 50
    NET_PACKET_ID_RGBCONTROLLER_RESIZEZONE = 1000
    NET_PACKET_ID_RGBCONTROLLER_UPDATELEDS = 1050
    NET_PACKET_ID_RGBCONTROLLER_UPDATEZONELEDS = 1051
    NET_PACKET_ID_RGBCONTROLLER_UPDATESINGLELED = 1052
    NET_PACKET_ID_RGBCONTROLLER_SETCUSTOMMODE = 1100
    NET_PACKET_ID_RGBCONTROLLER_UPDATEMODE = 1101


CT = TypeVar("CT", bound="RGBColor")


def parse_string(data: bytes, start: int = 0) -> Tuple[int, str]:
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


@dataclass
class RGBColor(object):
    red: int
    green: int
    blue: int

    def pack(self) -> bytearray:
        '''
        packs itself into bytes, ready to be sent to the SDK

        :returns: data ready to be sent
        '''
        return struct.pack("BBBx", self.red, self.green, self.blue)

    @classmethod
    def unpack(cls: Type[CT], data: bytearray, start: int = 0) -> Tuple[int, CT]:
        size = struct.calcsize("BBBx")
        if start == 0:
            r, g, b = struct.unpack("BBBx", data[:size])
            return size, RGBColor(r, g, b)
        else:
            r, g, b = struct.unpack("BBBx", data[start:start + size])
            return (start + size), RGBColor(r, g, b)

    @classmethod
    def fromHSV(cls: Type[CT], hue: int, saturation: int, value: int) -> CT:
        return RGBColor(*(round(i * 255) for i in colorsys.hsv_to_rgb(hue/360, saturation/100, value/100)))


def intToRGB(color: int) -> RGBColor:
    return RGBColor(color & 0x000000FF, (color >> 8) & 0x000000FF, (color >> 16) & 0x000000FF)


@dataclass
class LEDData(object):
    name: str
    value: int


@dataclass
class ModeData(object):
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
    colors: List[RGBColor]

    def pack(self) -> Tuple[int, bytearray]:
        '''
        Packs itself into bytes ready to be sent to the SDK

        :returns: data ready to be sent and its size
        '''
        # IDK why size = struct.calcsize(f"IiH{len(self.name)}si8IH{len(self.colors)}I")
        #  doesn't work without the if, but when self.colors is empty it still adds 2 bytes on for it
        if len(self.colors) == 0:
            size = struct.calcsize(f"IiH{len(self.name)}si8IH")
        else:
            size = struct.calcsize(f"IiH{len(self.name)}si8IH{len(self.colors)}I")
        data = struct.pack(
            f"IiH{len(self.name)}si8IH",
            size,
            self.id,
            len(self.name),
            self.name.encode('utf-8'),
            self.value,
            self.flags,
            self.speed_min,
            self.speed_max,
            self.colors_min,
            self.colors_max,
            self.speed,
            self.direction,
            self.color_mode,
            len(self.colors)
        )
        data += bytearray((color.pack() for color in self.colors))

        return size, data


@dataclass
class ZoneData(object):
    name: str
    zone_type: ZoneType
    leds_min: int
    leds_max: int
    num_leds: int
    mat_height: int
    mat_width: int
    matrix_map: List[list] = None
    leds: List[LEDData] = None
    colors: List[RGBColor] = None
    start_idx: int = None


@dataclass
class MetaData(object):
    description: str
    version: str
    serial: str
    location: str


@dataclass
class ControllerData(object):
    name: str
    metadata: MetaData
    device_type: DeviceType
    leds: list
    zones: list
    modes: list
    colors: list
    active_mode: int


class RGBObject(object):
    '''
    A parent object that includes a few generic functions that use the
    implementation provided by the children.
    '''

    def __init__(self, comms, name: str, device_id: int):
        self.comms = comms
        self.name = name
        self.id = device_id

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name}, id={self.id})"

    def set_color(self, color: RGBColor, start: int = 0, end: int = 0):
        pass

    def set_colors(self, colors: List[RGBColor], start: int = 0, end: int = 0):
        pass

    def clear(self):
        self.set_color(RGBColor(0, 0, 0))

    def off(self):
        self.clear()
