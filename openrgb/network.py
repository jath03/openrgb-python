#!/usr/bin/env python3
import socket
import struct
import threading
from openrgb import utils
from typing import Callable
from time import sleep


class NetworkClient(object):
    '''
    A class for interfacing with the OpenRGB SDK
    '''

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
        '''
        Listens for responses from the SDK from a separate thread

        :raises BrokenPipeError: when it loses connection to the SDK
        '''
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
        '''
        Sends the request for a device's data

        :param device: the id of the device to request data for
        '''
        self.send_header(device, utils.PacketType.NET_PACKET_ID_REQUEST_CONTROLLER_DATA, 0)

    def parseDeviceDescription(self, data: bytearray) -> utils.ControllerData:
        '''
        Parses the raw bytes received from the SDK into a ControllerData dataclass

        :param data: the raw data from a response to a request for device data
        :returns: a ControllerData dataclass ready to pass into the OpenRGBClient's calback function
        '''
        buff = struct.unpack("Ii", data[:struct.calcsize("Ii")])
        location = struct.calcsize("Ii")
        device_type = buff[1]
        metadata = []
        for x in range(5):
            location, val = utils.parse_string(data, location)
            metadata.append(val)
        buff = struct.unpack("=Hi", data[location:location + struct.calcsize("=Hi")])
        location += struct.calcsize("=Hi")
        num_modes = buff[0]
        active_mode = buff[-1]
        modes = []
        for x in range(num_modes):
            location, val = utils.parse_string(data, location)
            buff = list(struct.unpack("i8IH", data[location:location + struct.calcsize("i8IH")]))
            location += struct.calcsize("i8IH")
            colors = []
            for i in range(buff[-1]):
                location, color = utils.RGBColor.unpack(data, location)
                colors.append(color)
            modes.append(utils.ModeData(x, val.strip('\x00'), buff[0], utils.ModeFlags(buff[1]), *buff[2:7], utils.ModeDirections(buff[8]), utils.ModeColors(buff[9]), colors))
        num_zones = struct.unpack("H", data[location:location + struct.calcsize("H")])[0]
        location += struct.calcsize("H")
        zones = []
        for x in range(num_zones):
            location, val = utils.parse_string(data, location)
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
            location, name = utils.parse_string(data, location)
            value = struct.unpack("I", data[location:location + struct.calcsize("I")])[0]
            location += struct.calcsize("I")
            leds.append(utils.LEDData(name.strip("\x00"), value))
        num_colors = struct.unpack("H", data[location:location + struct.calcsize("H")])[0]
        location += struct.calcsize("H")
        colors = []
        for x in range(num_colors):
            location, color = utils.RGBColor.unpack(data, location)
            colors.append(color)
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

    def send_header(self, device_id: int, packet_type: int, packet_size: int):
        '''
        Sends a header to the SDK

        :param device_id: the id of the device to send a header for
        :param packet_type: a utils.PacketType
        :param packet_size: the full size of the data to be send after the header
        '''
        self.sock.send(struct.pack('ccccIII', b'O', b'R', b'G', b'B', device_id, packet_type, packet_size), socket.MSG_NOSIGNAL)
