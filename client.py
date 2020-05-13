#!/usr/bin/env python3
import socket
import struct
import threading
import typing
from time import sleep


NET_PACKET_ID_REQUEST_CONTROLLER_COUNT = 0
NET_PACKET_ID_REQUEST_CONTROLLER_DATA = 1
NET_PACKET_ID_SET_CLIENT_NAME = 50
NET_PACKET_ID_RGBCONTROLLER_RESIZEZONE = 1000
NET_PACKET_ID_RGBCONTROLLER_UPDATELEDS = 1050
NET_PACKET_ID_RGBCONTROLLER_UPDATEZONELEDS = 1051
NET_PACKET_ID_RGBCONTROLLER_UPDATESINGLELED = 1052
NET_PACKET_ID_RGBCONTROLLER_SETCUSTOMMODE = 1100
NET_PACKET_ID_RGBCONTROLLER_UPDATEMODE = 1101

HEADER_SIZE = 16


class NetworkClient(object):
    def __init__(self, update_callback, address="127.0.0.1", port=1337):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((address, port))

        self.listener = threading.Thread(target=self.listen)
        self.listener.start()

        self.callback = update_callback

        # Sending the client name
        name = b"python\0"
        self.send_header(0, NET_PACKET_ID_SET_CLIENT_NAME, len(name))
        self.sock.send(name, socket.MSG_NOSIGNAL)

        # Requesting the number of devices
        self.send_header(0, NET_PACKET_ID_REQUEST_CONTROLLER_COUNT, 0)

        self.send_header(3, NET_PACKET_ID_REQUEST_CONTROLLER_DATA, 0)

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
                if packet_type == NET_PACKET_ID_REQUEST_CONTROLLER_COUNT:
                    buff = struct.unpack("I", self.sock.recv(packet_size))
                    self.callback(device_id, packet_type, buff[0])
                elif packet_type == NET_PACKET_ID_REQUEST_CONTROLLER_DATA:
                    data = bytearray(packet_size)
                    self.sock.recv_into(data)
                    buff = struct.unpack("IiH", data[:struct.calcsize("IiH")])
                    location = struct.calcsize("IiH")
                    device_type = buff[1]
                    name = struct.unpack(f"{buff[-1]}s", data[location:(location+buff[-1])])[0].decode()
                    location += buff[-1]
                    print(device_type, name)

    def send_header(self, device_id: int, packet_type: int, packet_size: int):
        self.sock.send(struct.pack('ccccIII', b'O', b'R', b'G', b'B', device_id, packet_type, packet_size), socket.MSG_NOSIGNAL)


class OpenRGBClient(object):
    def __init__(self, address="127.0.0.1", port=1337):
        self.comms = NetworkClient(self.callback)
        self.device_num = 0

    def callback(self, device: int, type: int, data):
        if type == NET_PACKET_ID_REQUEST_CONTROLLER_COUNT:
            self.device_num = data



if __name__ == "__main__":
    client = OpenRGBClient()
    sleep(1)
    print(client.device_num)
