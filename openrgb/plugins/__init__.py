from __future__ import annotations
from typing import Optional
from openrgb.utils import Plugin
from openrgb.network import NetworkClient
from openrgb.plugins.common import ORGBPlugin

from openrgb.plugins.effects import EffectsPlugin

PLUGIN_NAMES = {
    "OpenRGB Effects Plugin": EffectsPlugin
}


def create_plugin(plugin: Plugin, comms: NetworkClient) -> Optional[ORGBPlugin]:
    plugin_class = PLUGIN_NAMES.get(plugin.name)
    if plugin_class is None:
        return None
    return plugin_class(plugin, comms)
