from enum import IntEnum, IntFlag
from typing import List, TypeVar, Tuple, BinaryIO
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


CT = TypeVar("CT", bound="RGBColor") # rgbColor Type
MDT = TypeVar("MDT", bound="ModeData") # ModeData Type
ZDT = TypeVar("ZDT", bound="ZoneData") # ZoneData Type
LDT = TypeVar("LDT", bound="LEDData") # LedData Type
MEDT = TypeVar("MEDT", bound="MetaData") # MEtaData Type
CDT = TypeVar("CDT", bound="ControllerData") # ControllerData Type
PT = TypeVar("PT", bound="Profile") # Profile Type


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


def pack_string(string: str) -> bytearray:
    '''
    Packs a string into bytes

    :param string: the string to pack
    :returns: bytes ready to be used
    '''
    num = len(string)
    return struct.pack(f"H{num}s", num + 1, string.encode('utf-8')) + b'\x00'


def parse_list(kind: object, data: bytearray, start: int = 0) -> Tuple[int, List]:
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
        start, thing = kind.unpack(data, start, x)
        things.append(thing)
    return start, things


def pack_list(things: list) -> bytearray:
    '''
    Packs a list of things using the things' .pack() methods

    :param things: a list of things to pack
    :returns: bytes ready to be used
    '''
    return bytes(struct.pack("H", len(things))) + b''.join(thing.pack() for thing in things)


@dataclass
class RGBColor(object):
    red: int
    green: int
    blue: int

    def pack(self) -> bytearray:
        '''
        Packs itself into a bytearray ready to be sent to the SDK or saved in a profile

        :returns: raw data ready to be sent or saved
        '''
        return struct.pack("BBBx", self.red, self.green, self.blue)

    @classmethod
    def unpack(cls, data: bytearray, start: int = 0, *args) -> Tuple[int, CT]:
        '''
        Unpacks an RGBColor object from bytes

        :returns: an RGBColor object
        '''
        size = struct.calcsize("BBBx")
        if start == 0:
            r, g, b = struct.unpack("BBBx", data[:size])
            return size, cls(r, g, b)
        else:
            r, g, b = struct.unpack("BBBx", data[start:start + size])
            return (start + size), cls(r, g, b)

    @classmethod
    def fromHSV(cls, hue: int, saturation: int, value: int) -> CT:
        '''
        Creates a RGBColor object from HSV values using colorsys
        '''
        return cls(*(round(i * 255) for i in colorsys.hsv_to_rgb(hue/360, saturation/100, value/100)))


@dataclass
class LEDData(object):
    name: str
    value: int

    def pack(self) -> bytearray:
        '''
        Packs itself into a bytearray ready to be sent to the SDK or saved in a profile

        :returns: raw data ready to be sent or saved
        '''
        return (
            pack_string(self.name)
            + struct.pack("I", self.value)
        )

    @classmethod
    def unpack(cls, data: bytearray, start: int = 0, *args) -> Tuple[int, LDT]:
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

    def pack(self) -> bytearray:
        '''
        Packs itself into a bytearray ready to be sent to the SDK or saved in a profile

        :returns: raw data ready to be sent or saved
        '''
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
        data += pack_list(self.colors)
        data = struct.pack("I", len(data) + struct.calcsize("I")) + data
        return data

    @classmethod
    def unpack(cls, data: bytearray, start: int = 0, index: int = 0) -> Tuple[int, MDT]:
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
        if (ModeFlags.MODE_FLAG_HAS_DIRECTION_HV in buff[1]
                or ModeFlags.MODE_FLAG_HAS_DIRECTION_UD in buff[1]
                or ModeFlags.MODE_FLAG_HAS_DIRECTION_LR in buff[1]):
            buff[7] = ModeDirections(buff[7])
        else:
            buff[7] = None
        if ModeFlags.MODE_FLAG_HAS_SPEED not in buff[1]:
            buff[2], buff[3], buff[6] = None, None, None
        if ModeFlags.MODE_FLAG_HAS_BRIGHTNESS not in buff[1]:
            buff[4], buff[5] = None, None

        buff[8] = ModeColors(buff[8])
        for i in range(buff[-1]):
            start, color = RGBColor.unpack(data, start)
            colors.append(color)
        return start, cls(index, val, *buff[:9], colors)


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

    def pack(self) -> bytearray:
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
    def unpack(cls, data: bytearray, start: int = 0, *args) -> Tuple[int, ZDT]:
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
        if buff[0] == ZoneType.ZONE_TYPE_MATRIX:
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
class MetaData(object):
    description: str
    version: str
    serial: str
    location: str

    def pack(self) -> bytearray:
        '''
        Packs itself into a bytearray ready to be sent to the SDK or saved in a profile

        :returns: raw data ready to be sent or saved
        '''
        return (
            pack_string(self.description)
            + pack_string(self.version)
            + pack_string(self.serial)
            + pack_string(self.location)
        )

    @classmethod
    def unpack(cls, data: bytearray, start: int = 0, *args) -> Tuple[int, MEDT]:
        '''
        Unpacks the raw data into a MetaData object

        :param data: The raw byte data to unpack
        :param start: What place in the data object to start
        '''
        buff = []
        for x in range(4):
            start, val = parse_string(data, start)
            buff.append(val)
        return start, cls(*buff)


@dataclass
class ControllerData(object):
    name: str
    metadata: MetaData
    device_type: DeviceType
    leds: List[LEDData]
    zones: List[ZoneData]
    modes: List[ModeData]
    colors: List[RGBColor]
    active_mode: int

    def pack(self) -> bytearray:
        '''
        Packs itself into a bytearray ready to be sent to the SDK or saved in a profile

        :returns: raw data ready to be sent or saved
        '''
        buff = (
            struct.pack("i", self.device_type)
            + pack_string(self.name)
            + self.metadata.pack()
            + struct.pack("H", len(self.modes))
            + struct.pack("i", self.active_mode)
            + b''.join(mode.pack()[struct.calcsize("Ii"):] for mode in self.modes)
            + pack_list(self.zones)
            + pack_list(self.leds)
            + pack_list(self.colors)
        )
        buff = struct.pack("I", len(buff) + struct.calcsize("I")) + buff
        return buff

    @classmethod
    def unpack(cls, data: bytearray, start: int = 0) -> CDT:
        '''
        Unpacks the raw bytes received from the SDK into a ControllerData dataclass

        :param data: The raw data from a response to a request for device data
        :returns: A ControllerData dataclass ready to pass into the OpenRGBClient's calback function
        '''
        buff = struct.unpack("Ii", data[start:start + struct.calcsize("Ii")])
        start += struct.calcsize("Ii")
        device_type = DeviceType(buff[1])
        start, name = parse_string(data, start)
        start, metadata = MetaData.unpack(data, start)
        buff = struct.unpack("=Hi", data[start:start + struct.calcsize("=Hi")])
        start += struct.calcsize("=Hi")
        num_modes = buff[0]
        active_mode = buff[-1]
        modes = []
        for x in range(num_modes):
            start, mode = ModeData.unpack(data, start, x)
            modes.append(mode)
        start, zones = parse_list(ZoneData, data, start)
        start, leds = parse_list(LEDData, data, start)
        start, colors = parse_list(RGBColor, data, start)
        for zone in zones:
            zone.leds = []
            zone.colors = []
            for x, led in enumerate(leds):
                if zone.name in led.name:
                    zone.leds.append(led)
                    zone.colors.append(colors[x])
                elif device_type == DeviceType.DEVICE_TYPE_KEYBOARD \
                        and zone.zone_type == ZoneType.ZONE_TYPE_MATRIX \
                        and led.name.lower().startswith("key"):
                    zone.leds.append(led)
                    zone.colors.append(colors[x])

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
class Profile(object):
    '''
    A dataclass to load, store, and pack the data found in an OpenRGB profile file.
    '''
    controllers: List[ControllerData]

    def pack(self) -> bytearray:
        data = bytearray()
        data += struct.pack("16sI", b'OPENRGB_PROFILE\x00', 1)
        for dev in self.controllers:
            data += dev.data.pack()
        return data

    @classmethod
    def unpack(cls, profile: BinaryIO) -> PT:
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
                new_data = ControllerData.unpack(profile.read(size))
                controllers.append(new_data)
            return cls(controllers)


class RGBObject(object):
    '''
    A parent class that includes a few generic functions that use the
    implementation provided by the children.
    '''

    def __init__(self, comms, name: str, device_id: int):
        self.comms = comms
        self.name = name
        self.id = device_id

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name}, id={self.id})"

    def set_color(self, color: RGBColor, start: int = 0, end: int = 0):
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
        Same as RGBObject.clear
        '''
        self.clear()
