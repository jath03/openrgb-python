#!/usr/bin/env python3
import socket
import struct
import threading
import constants
# from dataclasses import dataclass
from time import sleep


def intToRGB(color: int):
    return (color & 0x000000FF, (color >> 8) & 0x000000FF, (color >> 16) & 0x000000FF)


class NetworkClient(object):
    def __init__(self, update_callback, address="127.0.0.1", port=1337):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        for x in range(5):
            try:
                self.sock.connect((address, port))
                break
            except ConnectionRefusedError:
                if x < 4:
                    print("Unable to connect.  Is the OpenRGB SDK server started?")
                    print("Retrying in 5 seconds...\n")
                    sleep(5)
                elif x == 4:
                    raise

        self.listener = threading.Thread(target=self.listen)
        self.listener.start()

        self.callback = update_callback

        # Sending the client name
        name = b"python\0"
        self.send_header(0, constants.PacketType.NET_PACKET_ID_SET_CLIENT_NAME, len(name))
        self.sock.send(name, socket.MSG_NOSIGNAL)

        # Requesting the number of devices
        self.send_header(0, constants.PacketType.NET_PACKET_ID_REQUEST_CONTROLLER_COUNT, 0)

    def listen(self):
        while True:
            bytes_read = 0
            header = bytearray(HEADER_SIZE)
            self.sock.recv_into(header)

            # Unpacking the contents of the raw header struct into a list
            buff = list(struct.unpack('ccccIII', header))
            # print(buff[:4])
            if buff[:4] == [b'O', b'R', b'G', b'B']:
                device_id, packet_type, packet_size = buff[4:]
                # print(device_id, packet_type, packet_size)
                if packet_type == constants.PacketType.NET_PACKET_ID_REQUEST_CONTROLLER_COUNT:
                    buff = struct.unpack("I", self.sock.recv(packet_size))
                    self.callback(device_id, packet_type, buff[0])
                elif packet_type == constants.PacketType.NET_PACKET_ID_REQUEST_CONTROLLER_DATA:
                    data = bytearray(packet_size)
                    self.sock.recv_into(data)
                    self.parseDeviceDescription(data)
            sleep(.2)

    def requestDeviceData(self, device: int):
        self.send_header(device, constants.PacketType.NET_PACKET_ID_REQUEST_CONTROLLER_DATA, 0)

    def parseDeviceDescription(self, data):
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
            buff[4] = intToRGB(buff[4])
            buff[5] = intToRGB(buff[5])
            colors = []
            for x in range(buff[-1]):
                colors.append(intToRGB(struct.unpack("I", data[location:location + struct.calcsize("I")])))
                location += struct.calcsize('I')
            modes.append([val.strip('\x00'), *buff, colors])
        num_zones = struct.unpack("H", data[location:location + struct.calcsize("H")])[0]
        location += struct.calcsize("H")
        zones = []
        for x in range(num_zones):
            location, val = self.parseSizeAndString(data, location)
            buff = struct.unpack("iIIIH", data[location:location + struct.calcsize("iIIIH")])
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
            zones.append([val.strip('\x00'), *buff, width, height, matrix])
        num_leds = struct.unpack("H", data[location:location + struct.calcsize("H")])[0]
        location += struct.calcsize("H")
        leds = []
        for x in range(num_leds):
            location, name = self.parseSizeAndString(data, location)
            value = struct.unpack("I", data[location:location + struct.calcsize("I")])[0]
            location += struct.calcsize("I")
            leds.append([name.strip("\x00"), value])
        num_colors = struct.unpack("H", data[location:location + struct.calcsize("H")])[0]
        location += struct.calcsize("H")
        colors = []
        for x in range(num_colors):
            color = struct.unpack("I", data[location:location + struct.calcsize("I")])[0]
            location += struct.calcsize("I")
            colors.append(intToRGB((color)))
        print("Device Information:\n", "\tDevice type:", device_type, "\n\t", end="")
        print(*metadata, sep="\n\t")
        print("Mode Information:\n", "\tNumber of modes:", num_modes, "\n\tActive Mode:", active_mode, "\n\t", end="")
        print(*modes, sep='\n\t')
        print("Zone Information:\n", "\tNumber of zones:", num_zones, "\n\t", end="")
        print(*zones, sep='\n\t')
        print("LED Information:\n", "\tNumber of LEDs:", num_leds, "\n\t", end="")
        print(*leds, sep="\n\t")
        print("Color Information:\n", "\tNumber of Colors:", num_colors, "\n\t", end="")
        print(*colors, sep="\n\t")
        print("---------------------------------")

    def parseSizeAndString(self, data, start=0):
        size = struct.unpack('H', data[start:start + struct.calcsize('H')])[0]
        start += struct.calcsize("H")
        val = struct.unpack(f"{size}s", data[start:start + size])[0].decode()
        start += size
        return start, val

    def send_header(self, device_id: int, packet_type: int, packet_size: int):
        self.sock.send(struct.pack('ccccIII', b'O', b'R', b'G', b'B', device_id, packet_type, packet_size), socket.MSG_NOSIGNAL)


class OpenRGBClient(object):
    def __init__(self, address="127.0.0.1", port=1337):
        self.comms = NetworkClient(self.callback)
        self.device_num = 0
        while self.device_num == 0:
            sleep(.2)
        for x in range(self.device_num):
            self.comms.requestDeviceData(x)

    def callback(self, device: int, type: int, data):
        if type == constants.PacketType.NET_PACKET_ID_REQUEST_CONTROLLER_COUNT:
            self.device_num = data


if __name__ == "__main__":
    client = OpenRGBClient()
