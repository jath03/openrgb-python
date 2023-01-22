from __future__ import annotations
from openrgb import utils
from openrgb.network import NetworkClient
from dataclasses import dataclass
from typing import Iterator, Optional, Union, Type
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
        assert self.sdk_version == self.version

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


class EffectPacketType(IntEnum):
    REQUEST_EFFECT_LIST = 0
    START_EFFECT = 20
    STOP_EFFECT = 21


@dataclass
class Effect:
    name: str
    description: str
    enabled: bool

    @classmethod
    def unpack(cls, data: Iterator[int], version: int, *args) -> Effect:
        name = utils.parse_string(data)
        description = utils.parse_string(data)
        enabled = utils.parse_var('?', data)

        return cls(
            name,
            description,
            enabled
        )


class EffectsPlugin(ORGBPlugin):
    version = 1
    pkt_type_enum = EffectPacketType

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.effects = []

    def update(self):
        self.send_packet(EffectPacketType.REQUEST_EFFECT_LIST, request=True)
        self.comms.read()

    def recv(self, pkt_id: EffectPacketType, data: Iterator[int]):  # type: ignore
        if pkt_id == EffectPacketType.REQUEST_EFFECT_LIST:
            self.effects = utils.parse_list(Effect, data, self.version)

    def start_effect(self, effect: Union[int, str, Effect]):
        if type(effect) == int:
            effect = self.effects[effect]  # type: ignore
        elif type(effect) == str:
            try:
                effect = next(m for m in self.effects if m.name.lower() == effect.lower())  # type: ignore
            except StopIteration as e:
                raise ValueError(f"Effect `{effect}` not found") from e
        data = utils.pack_string(effect.name)  # type: ignore

        self.send_packet(EffectPacketType.START_EFFECT, data)

    def stop_effect(self, effect: Union[int, str, Effect]):
        if type(effect) == int:
            effect = self.effects[effect]  # type: ignore
        elif type(effect) == str:
            try:
                effect = next(m for m in self.effects if m.name.lower() == effect.lower())  # type: ignore
            except StopIteration as e:
                raise ValueError(f"Effect `{effect}` not found") from e
        data = utils.pack_string(effect.name)  # type: ignore

        self.send_packet(EffectPacketType.STOP_EFFECT, data)


PLUGIN_NAMES = {
    "OpenRGB Effects Plugin": EffectsPlugin
}


def create_plugin(plugin: utils.Plugin, comms: NetworkClient) -> ORGBPlugin:
    return PLUGIN_NAMES[plugin.name](plugin, comms)
