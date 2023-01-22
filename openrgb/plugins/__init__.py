from __future__ import annotations
from openrgb.utils import Plugin
from openrgb.network import NetworkClient
from openrgb.plugins.common import ORGBPlugin

from openrgb.plugins.effects import EffectsPlugin

PLUGIN_NAMES = {
    "OpenRGB Effects Plugin": EffectsPlugin
}


def create_plugin(plugin: Plugin, comms: NetworkClient) -> ORGBPlugin:
    return PLUGIN_NAMES[plugin.name](plugin, comms)