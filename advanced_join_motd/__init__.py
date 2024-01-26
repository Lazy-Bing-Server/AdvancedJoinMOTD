from advanced_join_motd.advanced_join_motd import AdvancedJoinMOTD
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcdreforged.api.all import *


__main = AdvancedJoinMOTD.get_instance()


def on_load(server: "PluginServerInterface", prev_module):
    __main.on_load(server, prev_module)
