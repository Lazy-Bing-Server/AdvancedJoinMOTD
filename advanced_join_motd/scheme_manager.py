import importlib
import importlib.util
import os
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Type, Iterable, Optional
import gc
import sys

from mcdreforged.api.event import MCDRPluginEvents
from mcdreforged.api.types import PluginServerInterface, Info
from mcdreforged.api.rtext import RColor

from advanced_join_motd.utils import file_util
from advanced_join_motd.utils.translation import rtr, MessageText

if TYPE_CHECKING:
    from advanced_join_motd.advanced_join_motd import AdvancedJoinMOTD
    from advanced_join_motd.api import AbstractJoinMOTDScheme


class SchemeManager:
    DIR = 'schemes'

    def __init__(self, plugin_inst: "AdvancedJoinMOTD"):
        self.__inst = plugin_inst
        self.__schemes: Dict[str, "AbstractJoinMOTDScheme"] = {}
        self.__modules = {}
        file_util.ensure_dir(self.dir_path)

    @property
    def dir_path(self):
        return os.path.join(self.__inst.get_data_folder(), self.DIR)

    @property
    def schemes(self):
        return self.__schemes

    def get_dir_module_path(self, *args):
        return '.'.join(list(Path(self.dir_path).parts) + list(args))

    def register_scheme(self, scheme: Type["AbstractJoinMOTDScheme"], server: PluginServerInterface):
        if scheme.get_name() in self.__schemes.keys():
            return self.__inst.logger.error(f"Duplicated name scheme found: {scheme.get_name()}")
        scheme_instance = scheme(self.__inst, server)
        self.__schemes[scheme.get_name()] = scheme_instance
        self.__inst.logger.info(f'Registered scheme {scheme.get_name()}')
        return scheme_instance

    def unregister_scheme(self, scheme: "AbstractJoinMOTDScheme"):
        name = scheme.get_name()
        del self.__schemes[name]

    """def register_all_schemes(self):
        for item in os.listdir(self.dir_path):
            path = os.path.join(self.dir_path, item)
            if os.path.isfile(path) and item.endswith('.py'):
                self.__inst.logger.debug(f"Importing module: {path}")
                try:
                    module_name = f'__AJM__@{item[:-3]}'
                    spec = importlib.util.spec_from_file_location(module_name, path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self.__modules[module_name] = module
                    sys.modules[module_name] = module
                    self.__inst.logger.debug(f"Imported scheme module: {path}")
                except Exception as exc:
                    self.__inst.logger.exception(f'Import scheme python module "{path}" failed', exc_info=exc)
                    continue"""

    def get_available_schemes(self, player: str, info: Optional[Info] = None) -> Iterable["AbstractJoinMOTDScheme"]:
        return filter(lambda s: s.is_enabled(player, info), self.__schemes.values())

    # Ra1ny_Yuki[/127.0.0.1:7890] logged in with entity id 1 at (1, 2, 3)
    def on_player_joined(self, server: PluginServerInterface, player: Optional[str] = None, info: Optional[Info] = None):
        def tell(msg: MessageText):
            if player is None:
                return self.__inst.logger.info(msg)
            return server.tell(player, msg)

        self.__inst.logger.debug('Generating player join message')
        schemes = self.get_available_schemes(player, info)
        for scheme in sorted(schemes, reverse=True):  # type: AbstractJoinMOTDScheme
            try:
                return tell('\n' + scheme.get_scheme_text(player or 'Console', info))
            except Exception as exc:
                tell(
                    (rtr(
                        'preview.generated_failed',
                        scheme_name=scheme.get_name()
                    ) + str(exc)).set_color(RColor.red)
                )
                self.__inst.logger.exception(f"Error generate MOTD text with scheme {scheme.get_name()}", exc_info=exc)

        tell(rtr('preview.no_avail', plugin_name=self.__inst.server.get_self_metadata().name))

    def on_unload(self, server: PluginServerInterface):
        for name, module in self.__modules.keys():
            del sys.modules[name]

    def on_refresh(self):
        for scheme in self.__schemes.values():
            scheme.on_refresh()

    def on_load(self, server: PluginServerInterface):
        # self.register_all_schemes()
        self.__inst.logger.debug('Registering on_player_join event')
        server.register_event_listener(MCDRPluginEvents.PLAYER_JOINED, self.on_player_joined)
