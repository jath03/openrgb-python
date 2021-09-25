from openrgb import utils
from openrgb.network import NetworkClient
import struct


class ORGBPlugin:
    version = -1

    def __init__(self, plugin_data: utils.Plugin, comms: NetworkClient):
        self.name = plugin_data.name
        self.description = plugin_data.description
        self.plugin_version = plugin_data.version
        self.commit = plugin_data.commit
        self.url = plugin_data.url
        self.id = plugin_data.id
        self.sdk_version = plugin_data.sdk_version
        self.comms = comms
        assert self.sdk_version == self.version

    def send_packet(self, packet_type: int, data: bytes):
        self.comms.send_header(0, utils.PacketType.PLUGIN_SPECIFIC, len(data) + struct.calcsize('II'))
        data = struct.pack('II', self.id, packet_type) + data
        self.comms.send_data(data)


class Effects(ORGBPlugin):
    version = 1

    def get_effects(self):
        self.send_packet(1, bytes(b'hi'))


PLUGIN_NAMES = {
    "OpenRGB Effects Plugin": Effects
}


def create_plugin(plugin: utils.Plugin, comms: NetworkClient) -> ORGBPlugin:
    return PLUGIN_NAMES[plugin.name](plugin, comms)
