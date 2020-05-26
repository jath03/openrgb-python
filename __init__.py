#!/usr/bin/env python3
import socket
import struct
import threading
from openrgb import utils
from typing import Callable, List, Union
# from dataclasses import dataclass
from time import sleep


class NetworkClient(object):
    def __init__(self, update_callback: Callable, address: str = "127.0.0.1", port: int = 1337, name: str = "openrgb-python"):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        for x in range(5):
            try:
                self.sock.connect((address, port))
                break
            except ConnectionRefusedError:
                # if x < 4:
                print("Unable to connect.  Is the OpenRGB SDK server started?")
                print("Retrying in 5 seconds...\n")
                sleep(5)
                # elif x == 4:
                #     raise

        self.listener = threading.Thread(target=self.listen)
        self.listener.daemon = True
        self.listener.start()

        self.callback = update_callback

        # Sending the client name
        name = bytes(f"{name}\0", 'utf-8')
        self.send_header(0, utils.PacketType.NET_PACKET_ID_SET_CLIENT_NAME, len(name))
        self.sock.send(name, socket.MSG_NOSIGNAL)

        # Requesting the number of devices
        self.send_header(0, utils.PacketType.NET_PACKET_ID_REQUEST_CONTROLLER_COUNT, 0)

    def listen(self):
        try:
            while True:
                header = bytearray(utils.HEADER_SIZE)
                self.sock.recv_into(header)

                # Unpacking the contents of the raw header struct into a list
                buff = list(struct.unpack('ccccIII', header))
                # print(buff[:4])
                if buff[:4] == [b'O', b'R', b'G', b'B']:
                    device_id, packet_type, packet_size = buff[4:]
                    # print(device_id, packet_type, packet_size)
                    if packet_type == utils.PacketType.NET_PACKET_ID_REQUEST_CONTROLLER_COUNT:
                        buff = struct.unpack("I", self.sock.recv(packet_size))
                        self.callback(device_id, packet_type, buff[0])
                    elif packet_type == utils.PacketType.NET_PACKET_ID_REQUEST_CONTROLLER_DATA:
                        data = bytearray(packet_size)
                        self.sock.recv_into(data)
                        self.callback(device_id, packet_type, self.parseDeviceDescription(data))
                sleep(.2)
        except BrokenPipeError:
            raise Exception("Disconnected.  Did you disable the SDK?")

    def requestDeviceData(self, device: int):
        self.send_header(device, utils.PacketType.NET_PACKET_ID_REQUEST_CONTROLLER_DATA, 0)

    def parseDeviceDescription(self, data: bytearray) -> utils.ControllerData:
        buff = struct.unpack("Ii", data[:struct.calcsize("Ii")])
        location = struct.calcsize("Ii")
        device_type = buff[1]
        metadata = []
        for x in range(5):
            location, val = self.parseSizeAndString(data, location)
            metadata.append(val)
        buff = struct.unpack("=Hi", data[location:location + struct.calcsize("=Hi")])
        location += struct.calcsize("=Hi")
        num_modes = buff[0]
        active_mode = buff[-1]
        modes = []
        for x in range(num_modes):
            location, val = self.parseSizeAndString(data, location)
            buff = list(struct.unpack("i8IH", data[location:location + struct.calcsize("i8IH")]))
            location += struct.calcsize("i8IH")
            buff[4] = utils.intToRGB(buff[4])
            buff[5] = utils.intToRGB(buff[5])
            colors = []
            for x in range(buff[-1]):
                colors.append(utils.intToRGB(struct.unpack("I", data[location:location + struct.calcsize("I")])[0]))
                location += struct.calcsize('I')
            modes.append(utils.ModeData(val.strip('\x00'), buff[0], utils.ModeFlags(buff[1]), *buff[2:7], utils.ModeDirections(buff[8]), utils.ModeColors(buff[9]), colors))
        num_zones = struct.unpack("H", data[location:location + struct.calcsize("H")])[0]
        location += struct.calcsize("H")
        zones = []
        for x in range(num_zones):
            location, val = self.parseSizeAndString(data, location)
            buff = list(struct.unpack("iIIIH", data[location:location + struct.calcsize("iIIIH")]))
            location += struct.calcsize("iIIIH")

            height, width = 0, 0
            matrix = [[]]
            if buff[-1] > 0:
                height, width = struct.unpack("II", data[location:location + struct.calcsize("II")])
                location += struct.calcsize("II")
                matrix = [[] for x in height]
                for y in range(height):
                    for x in range(width):
                        matrix[y][x] = struct.unpack("I", data[location:location + struct.calcsize("I")])
                        location += struct.calcsize("I")
            zones.append(utils.ZoneData(val.strip('\x00'), utils.ZoneType(buff[0]), *buff[1:-1], height, width, matrix))
        num_leds = struct.unpack("H", data[location:location + struct.calcsize("H")])[0]
        location += struct.calcsize("H")
        leds = []
        for x in range(num_leds):
            location, name = self.parseSizeAndString(data, location)
            value = struct.unpack("I", data[location:location + struct.calcsize("I")])[0]
            location += struct.calcsize("I")
            leds.append(utils.LEDData(name.strip("\x00"), value))
        num_colors = struct.unpack("H", data[location:location + struct.calcsize("H")])[0]
        location += struct.calcsize("H")
        colors = []
        for x in range(num_colors):
            color = struct.unpack("I", data[location:location + struct.calcsize("I")])[0]
            location += struct.calcsize("I")
            colors.append(utils.intToRGB((color)))
        for zone in zones:
            zone.leds = []
            zone.colors = []
            for x in range(len(leds)):
                if zone.name in leds[x].name:
                    zone.leds.append(leds[x])
                    zone.colors.append(colors[x])
        # print("Device Information:\n", "\tDevice type:", device_type, "\n\t", end="")
        # print(*metadata, sep="\n\t")
        # print("Mode Information:\n", "\tNumber of modes:", num_modes, "\n\tActive Mode:", active_mode, "\n\t", end="")
        # print(*modes, sep='\n\t')
        # print("Zone Information:\n", "\tNumber of zones:", num_zones, "\n\t", end="")
        # print(*zones, sep='\n\t')
        # print("LED Information:\n", "\tNumber of LEDs:", num_leds, "\n\t", end="")
        # print(*leds, sep="\n\t")
        # print("Color Information:\n", "\tNumber of Colors:", num_colors, "\n\t", end="")
        # print(*colors, sep="\n\t")
        # print("---------------------------------")
        return utils.ControllerData(
            metadata[0],
            utils.MetaData(*metadata[1:]),
            utils.DeviceType(device_type),
            leds,
            zones,
            modes,
            colors,
            active_mode
        )

    def parseSizeAndString(self, data, start=0):
        size = struct.unpack('H', data[start:start + struct.calcsize('H')])[0]
        start += struct.calcsize("H")
        val = struct.unpack(f"{size}s", data[start:start + size])[0].decode()
        start += size
        return start, val.strip("\x00")

    def send_header(self, device_id: int, packet_type: int, packet_size: int):
        self.sock.send(struct.pack('ccccIII', b'O', b'R', b'G', b'B', device_id, packet_type, packet_size), socket.MSG_NOSIGNAL)


# class RGBController(object):
#     def __init__(self, data: utils.ControllerData, device_id: int, network_client: NetworkClient):
#         self.data = data
#         self.id = device_id
#         self.comms = network_client
#
#     def __repr__(self):
#         return f"RGBController(name={self.data.name}, id={self.id})"
#
#     def set_color(self, color: Union[utils.RGBColor, utils.HSVColor], start=0, end=0):
#         if end == 0:
#             end = len(self.data.leds)
#         self.comms.send_header(self.id, utils.PacketType.NET_PACKET_ID_RGBCONTROLLER_UPDATELEDS, struct.calcsize(f"IH{3*(end - start)}b{(end - start)}x"))
#         buff = struct.pack("H", end - start) + (color.pack())*(end - start)
#         buff = struct.pack("I", len(buff)) + buff
#         self.comms.sock.send(buff)
#
#     def set_colors(self, colors: List(Union[utils.RGBColor, utils.HSVColor]), start=0, end=0):
#         if end == 0:
#             end = len(self.data.leds)
#         if len(colors) != (end - start):
#             raise IndexError("Number of colors doesn't match number of LEDs")
#         self.comms.send_header(self.id, utils.PacketType.NET_PACKET_ID_RGBCONTROLLER_UPDATELEDS, struct.calcsize(f"IH{3*(end - start)}b{(end - start)}x"))
#         buff = struct.pack("H", end - start) + tuple(color.pack() for color in colors)
#         buff = struct.pack("I", len(buff)) + buff
#         self.comms.sock.send(buff)
#
#     def set_led_color(self, led: int, color: Union[utils.RGBColor, utils.HSVColor]):
#         if led > len(self.data.leds):
#             raise IndexError("LED out of range")
#         self.comms.send_header(self.id, utils.PacketType.NET_PACKET_ID_RGBCONTROLLER_UPDATESINGLELED, struct.calcsize(f"iBBBx"))
#         self.comms.sock.send(struct.pack("i", led) + color.pack())
#
#     def clear(self):
#         self.set_color(Union[utils.RGBColor, utils.HSVColor](0, 0, 0))

class LED(utils.RGBObject):
    pass


class Zone(utils.RGBObject):
    def __init__(self, data: utils.ZoneData, zone_id: int, device_id: int, network_client: NetworkClient):
        self.name = data.name
        self.type = data.zone_type
        self.leds = data.leds
        self.mat_width = data.mat_width
        self.mat_height = data.mat_height
        self.matrix_map = data.matrix_map
        self.colors = data.colors
        self.device_id = device_id
        self.comms = network_client
        self.id = zone_id

    def set_color(self, color: Union[utils.RGBColor, utils.HSVColor], start: int = 0, end: int = 0):
        if end == 0:
            end = len(self.leds)
        self.comms.send_header(self.device_id, utils.PacketType.NET_PACKET_ID_RGBCONTROLLER_UPDATEZONELEDS, struct.calcsize(f"IIH{3*(end - start)}b{(end - start)}x"))
        buff = struct.pack("IH", self.id, end - start) + (color.pack())*(end - start)
        buff = struct.pack("I", len(buff)) + buff
        self.comms.sock.send(buff)

class Device(utils.RGBObject):
    def __init__(self, data: utils.ControllerData, device_id: int, network_client: NetworkClient):
        self.name = data.name
        self.metadata = data.metadata
        self.type = data.device_type
        self.leds = data.leds
        self.zones = [Zone(data.zones[x], x, device_id, network_client) for x in range(len(data.zones))]
        self.modes = data.modes
        self.colors = data.colors
        self.active_mode = data.active_mode
        self.id = device_id
        self.comms = network_client

    def set_color(self, color: Union[utils.RGBColor, utils.HSVColor], start: int = 0, end: int = 0):
        self._set_color(
            self.leds,
            utils.PacketType.NET_PACKET_ID_RGBCONTROLLER_UPDATELEDS,
            color,
            start,
            end
        )

    def set_colors(self, colors: List[Union[utils.RGBColor, utils.HSVColor]], start: int = 0, end: int = 0):
        self._set_colors(
            self.leds,
            utils.PacketType.NET_PACKET_ID_RGBCONTROLLER_UPDATELEDS,
            colors,
            start,
            end
        )


class OpenRGBClient(object):
    def __init__(self, address: str = "127.0.0.1", port: int = 1337, name: str = "openrgb-python"):
        self.comms = NetworkClient(self.callback, address, port, name)
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

    def callback(self, device: int, type: int, data):
        if type == utils.PacketType.NET_PACKET_ID_REQUEST_CONTROLLER_COUNT:
            self.device_num = data
        elif type == utils.PacketType.NET_PACKET_ID_REQUEST_CONTROLLER_DATA:
            if self.devices[device] is None:
                self.devices[device] = Device(data, device, self.comms)
            else:
                self.devices[device].data = data

    def set_color(self, color: Union[utils.RGBColor, utils.HSVColor]):
        for device in self.devices:
            device.set_color(color)

    def clear(self):
        self.set_color(Union[utils.RGBColor, utils.HSVColor](0, 0, 0))

    def off(self):
        self.clear()

    def get_devices_by_type(self, type: utils.DeviceType) -> List[Device]:
        return [device for device in self.devices if device.type == type]

__all__ = ['utils']

if __name__ == "__main__":
    client = OpenRGBClient()
    for controller in client.devices:
        print(controller, "ID: " + str(controller.id), controller.data.device_type, sep='\n\t')
    # client.devices[4].set_led_color(1, Union[utils.RGBColor, utils.HSVColor](0, 255, 0))
