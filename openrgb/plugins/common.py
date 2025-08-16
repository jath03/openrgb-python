from __future__ import annotations
from openrgb import utils
from openrgb.network import NetworkClient
from typing import Iterator, Optional, Type
from enum import IntEnum
import struct


class ORGBPlugin:
    version = -1
    pkt_type_enum = object()

    def __init__(self, plugin_data: utils.Plugin, comms: NetworkClient):
        self.name = plugin_data.name
        self.description = plugin_data.description
        self.plugin_version = plugin_data.version
        self.id = plugin_data.id
        self.sdk_version = plugin_data.sdk_version
        self.comms = comms
        assert self.sdk_version <= self.version

    def __repr__(self):
        return type(self).__name__

    def send_packet(self, packet_type: int, data: Optional[bytes] = None, request: bool = False):
        if not data:
            data = bytes()
        self.comms.send_header(self.id, utils.PacketType.PLUGIN_SPECIFIC, len(data) + struct.calcsize('I'), not request)
        data = struct.pack('I', packet_type) + data
        self.comms.send_data(data, not request)

    def _recv(self, data: Iterator[int]):
        pkt_id = self.pkt_type_enum(utils.parse_var('I', data))  # type: ignore
        self.recv(pkt_id, data)

    def recv(self, pkt_id: Type[IntEnum], data: Iterator[int]):
        # To be implemented per plugin
        pass

    def update(self):
        # Optional, called with `OpenRGBClient.update_plugins`
        pass
