from enum import IntEnum, IntFlag
from typing import List, TypeVar, Type
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
    def unpack(cls: Type[CT], data: bytearray) -> CT:
        r, g, b = struct.unpack("BBBx", data)
        return RGBColor(r, g, b)

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
    def __init__(self, comms, name: str, device_id: int):
        self.comms = comms
        self.name = name
        self.id = device_id

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name}, id={self.id})"

    def set_color(self, color: RGBColor, start: int = 0, end: int = 0):
        pass

    def _set_color(self, children: list, type: PacketType, color: RGBColor, start: int = 0, end: int = 0):
        if end == 0:
            end = len(children)
        self.comms.send_header(self.id, type, struct.calcsize(f"IH{3*(end - start)}b{(end - start)}x"))
        buff = struct.pack("H", end - start) + (color.pack())*(end - start)
        buff = struct.pack("I", len(buff)) + buff
        self.comms.sock.send(buff)

    def set_colors(self, colors: List[RGBColor], start: int = 0, end: int = 0):
        pass

    def _set_colors(self, children: list, type: PacketType, colors: List[RGBColor], start: int = 0, end: int = 0):
        if end == 0:
            end = len(children)
        if len(colors) != (end - start):
            raise IndexError("Number of colors doesn't match number of LEDs")
        self.comms.send_header(self.id, type, struct.calcsize(f"IH{3*(end - start)}b{(end - start)}x"))
        buff = struct.pack("H", end - start) + b''.join((color.pack() for color in colors))
        buff = struct.pack("I", len(buff)) + buff
        self.comms.sock.send(buff)

    def clear(self):
        self.set_color(RGBColor(0, 0, 0))

    def off(self):
        self.clear()
