from __future__ import annotations
import platform
import socket
import struct
import threading
from openrgb import utils
from typing import Callable

OPENRGB_PROTOCOL_VERSION = 3

if platform.system() == "Linux":
    NOSIGNAL: int = socket.MSG_NOSIGNAL
else:
    NOSIGNAL = 0


class NetworkClient:
    '''
    A class for interfacing with the OpenRGB SDK
    '''

    def __init__(self, update_callback: Callable, address: str = "127.0.0.1", port: int = 6742, name: str = "openrgb-python", protocol_version: int = None):
        '''
        :param update_callback: the function to call when data is received
        :param address: the ip address of the SDK server
        :param port: the port of the SDK server
        :param name: the string that will be displayed on the OpenRGB SDK tab's list of clients
        '''
        self.lock = threading.Lock()
        self.callback = update_callback
        self.sock = None
        self.max_protocol_version = OPENRGB_PROTOCOL_VERSION
        if protocol_version is not None:
            if protocol_version > self.max_protocol_version:
                raise utils.SDKVersionError(f"Requested protocol version {protocol_version} is greater than maximum supported version {self.max_protocol_version}")
            self._protocol_version = protocol_version
        else:
            self._protocol_version = OPENRGB_PROTOCOL_VERSION
        self.address = address
        self.port = port
        self.name = name
        self.start_connection()

    def start_connection(self):
        '''
        Initializes a socket, connects to the SDK, and sets the client name
        '''
        if self.sock is not None:
            return
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(1.0)

        try:
            self.sock.connect((self.address, self.port))
        except OSError:
            self.sock = None
            raise

        # Checking server protocol version
        self.send_header(0, utils.PacketType.REQUEST_PROTOCOL_VERSION, struct.calcsize('I'))
        self.send_data(struct.pack("I", self._protocol_version), False)
        try:
            self.read()
        except socket.timeout:
            self._protocol_version = 0
            self.lock.release()
        self.sock.settimeout(10.0)
        # Sending the client name
        name = bytes(f"{self.name}\0", 'utf-8')
        self.send_header(0, utils.PacketType.SET_CLIENT_NAME, len(name))
        self.send_data(name)

    def stop_connection(self):
        '''
        Closes the active socket
        '''
        try:
            self.lock.release()
        except Exception:
            pass

        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def read(self):
        '''
        Reads responses from the SDK

        :raises utils.OpenRGBDisconnected: when it loses connection to the SDK
        '''
        if not self.connected:
            raise utils.OpenRGBDisconnected()
        header = bytearray(utils.HEADER_SIZE)
        try:
            self.sock.recv_into(header)
        except utils.CONNECTION_ERRORS as e:
            self.stop_connection()
            raise utils.OpenRGBDisconnected() from e

        if header == '\x00'*utils.HEADER_SIZE:
            self.stop_connection()
            raise utils.OpenRGBDisconnected()
        # Unpacking the contents of the raw header struct into a list
        buff = list(struct.unpack('ccccIII', header))

        # Checking packet signature
        if buff[:4] == [b'O', b'R', b'G', b'B']:
            device_id, packet_type, packet_size = buff[4:]

            # Parse information from each packet type
            if packet_type == utils.PacketType.REQUEST_CONTROLLER_COUNT:
                try:
                    buff = struct.unpack("I", self.sock.recv(packet_size))
                    self.lock.release()
                    self.callback(device_id, packet_type, buff[0])
                except utils.CONNECTION_ERRORS as e:
                    self.stop_connection()
                    raise utils.OpenRGBDisconnected() from e
                finally:
                    try:
                        self.lock.release()
                    except RuntimeError:
                        pass

            elif packet_type == utils.PacketType.REQUEST_CONTROLLER_DATA:
                try:
                    data = bytes()
                    while len(data) < packet_size:
                        data += self.sock.recv(packet_size - len(data))
                except utils.CONNECTION_ERRORS as e:
                    self.stop_connection()
                    raise utils.OpenRGBDisconnected() from e
                finally:
                    self.lock.release()
                try:
                    self.callback(device_id, packet_type, utils.ControllerData.unpack(data, self._protocol_version))
                except utils.PARSING_ERRORS as e:
                    raise utils.ControllerParsingError(f"Unable to parse data from request `{packet_type}` for device #{device_id}") from e

            elif packet_type == utils.PacketType.DEVICE_LIST_UPDATED:
                assert device_id == 0 and packet_size == 0
                self.read()
                self.callback(device_id, packet_type, 0)

            elif packet_type == utils.PacketType.REQUEST_PROTOCOL_VERSION:
                try:
                    self.max_protocol_version = min(struct.unpack("I", self.sock.recv(packet_size))[0], OPENRGB_PROTOCOL_VERSION)
                    self._protocol_version = min(self.max_protocol_version, self._protocol_version)
                except utils.CONNECTION_ERRORS as e:
                    self.stop_connection()
                    raise utils.OpenRGBDisconnected() from e
                finally:
                    self.lock.release()

            elif packet_type == utils.PacketType.REQUEST_PROFILE_LIST:
                try:
                    data = bytes()
                    while len(data) < packet_size:
                        data += self.sock.recv(packet_size - len(data))
                    idata = iter(data)
                    for _ in range(4):
                        next(idata)
                except utils.CONNECTION_ERRORS as e:
                    self.stop_connection()
                    raise utils.OpenRGBDisconnected() from e
                finally:
                    self.lock.release()
                self.callback(device_id, packet_type, utils.parse_list(utils.Profile, idata, self._protocol_version))

    def requestDeviceData(self, device: int):
        '''
        Sends the request for a device's data

        :param device: the id of the device to request data for
        '''
        if not self.connected:
            raise utils.OpenRGBDisconnected()
        self.send_header(device, utils.PacketType.REQUEST_CONTROLLER_DATA, struct.calcsize('I'))
        self.send_data(struct.pack("I", self._protocol_version), False)
        self.read()

    def requestDeviceNum(self):
        '''
        Requesting the number of devices from the SDK server
        '''
        self.send_header(0, utils.PacketType.REQUEST_CONTROLLER_COUNT, 0)
        self.read()

    def requestProfileList(self):
        '''
        Sends the request for the available profiles
        '''
        self.send_header(0, utils.PacketType.REQUEST_PROFILE_LIST, 0)
        self.read()

    def send_header(self, device_id: int, packet_type: utils.PacketType, packet_size: int):
        '''
        Sends a header to the SDK

        :param device_id: The id of the device to send a header for
        :param packet_type: A utils.PacketType
        :param packet_size: The full size of the data to be sent after the header
        '''
        self.check_version(packet_type)
        if not self.connected:
            raise utils.OpenRGBDisconnected()

        if not self.lock.acquire(timeout=10):
            raise utils.OpenRGBDisconnected("SDK server did not respond to previous request")

        try:
            data = struct.pack('ccccIII', b'O', b'R', b'G', b'B', device_id, packet_type, packet_size)
            sent = self.sock.send(data, NOSIGNAL)  # type: ignore
            if sent != len(data):
                self.stop_connection()
                raise utils.OpenRGBDisconnected()
            if packet_size == 0 and packet_type not in (utils.PacketType.REQUEST_CONTROLLER_COUNT,
                                                        utils.PacketType.REQUEST_CONTROLLER_DATA,
                                                        utils.PacketType.REQUEST_PROTOCOL_VERSION,
                                                        utils.PacketType.REQUEST_PROFILE_LIST):
                self.lock.release()
        except utils.CONNECTION_ERRORS as e:
            self.stop_connection()
            raise utils.OpenRGBDisconnected() from e

    def send_data(self, data: bytes, release_lock: bool = True):
        '''
        Sends data to the SDK

        :param data: The data to send
        '''
        if not self.connected:
            raise utils.OpenRGBDisconnected()
        try:
            sent = self.sock.send(data, NOSIGNAL)  # type: ignore
            if sent != len(data):
                self.stop_connection()
                raise utils.OpenRGBDisconnected()
            if release_lock:
                self.lock.release()
        except utils.CONNECTION_ERRORS as e:
            self.stop_connection()
            raise utils.OpenRGBDisconnected() from e

    def check_version(self, packet_type: utils.PacketType):
        '''
        Verifies that the packet type is supported on the version we are using.

        :param packet_type: What kind of packet is going to be sent
        :raises utils.SDKVersionError: When a packet is unsupported
        '''
        if self._protocol_version < 2 and packet_type in (utils.PacketType.REQUEST_PROFILE_LIST,
                                                          utils.PacketType.REQUEST_SAVE_PROFILE,
                                                          utils.PacketType.REQUEST_LOAD_PROFILE,
                                                          utils.PacketType.REQUEST_DELETE_PROFILE):
            raise utils.SDKVersionError("Profile controls not supported on protoocl versions < 2.  You probably need to update OpenRGB")
        elif self._protocol_version < 3 and packet_type == utils.PacketType.RGBCONTROLLER_SAVEMODE:
            raise utils.SDKVersionError("Saving modes not supported on protoocl versions < 3.  You probably need to update OpenRGB")

    @property
    def connected(self) -> bool:
        '''
        Returns whether the current instance is currently connected to a server
        '''
        return self.sock is not None
