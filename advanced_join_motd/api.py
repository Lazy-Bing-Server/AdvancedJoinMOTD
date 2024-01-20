import json
import os.path
from abc import ABC, abstractmethod
from threading import RLock
from typing import Type, Optional

import ruamel.yaml
from mcdreforged.api.types import Info, ServerInterface, PluginServerInterface
from mcdreforged.api.event import MCDRPluginEvents

from advanced_join_motd.utils.translation import MessageText
from advanced_join_motd.advanced_join_motd import AdvancedJoinMOTD
from advanced_join_motd.utils import file_util
from advanced_join_motd.utils import translation


__all__ = [
    "AbstractJoinMOTDScheme",
    "translation",
    "register_scheme"
]


class AbstractJoinMOTDScheme(ABC):
    @staticmethod
    @abstractmethod
    def get_name() -> str:
        ...

    @staticmethod
    def get_priority() -> int:
        return 1000

    def __init__(self, plugin_inst: AdvancedJoinMOTD, server: PluginServerInterface):
        self.__lock = RLock()
        self.__inst = plugin_inst
        self.__scheme_psi = server

    @property
    def server(self):
        return self.__scheme_psi

    @property
    def logger(self):
        return self.__inst.logger

    @property
    def translation_prefix(self):
        return f"{self.server.get_self_metadata().id}"

    @abstractmethod
    def is_enabled(self, player: str, info: Optional[Info] = None) -> bool:
        ...

    @abstractmethod
    def get_scheme_text(self, player: str, info: Optional[Info] = None) -> MessageText:
        ...

    def get_data_folder(self):
        return self.server.get_data_folder()

    def __lt__(self, other: "AbstractJoinMOTDScheme"):
        return self.get_priority() < other.get_priority()

    def rtr(self, translation_key: str, *args, _lb_rtr_prefix: Optional[str] = None, **kwargs):
        _lb_rtr_prefix = _lb_rtr_prefix or f'{self.translation_prefix}.'
        return translation.rtr(translation_key, *args, _lb_rtr_prefix=_lb_rtr_prefix, **kwargs)

    def register_translations(self):
        translation_folder = file_util.ensure_dir(os.path.join(self.get_data_folder(), 'lang'))
        self.logger.debug(f'Files in translation folder: {os.listdir(translation_folder)}')
        for file in os.listdir(translation_folder):
            path = os.path.join(translation_folder, file)
            if not os.path.isfile(path):
                self.logger.debug("")
                continue
            lang, translation_mapping = None, None
            if file.endswith('.json'):
                lang = file[:-5]
                with open(path, encoding='utf8') as f:
                    translation_mapping = json.load(f)
            elif file.endswith('.yml') or file.endswith('.yaml'):
                self.logger.debug(f'Found language file {file}')
                lang = file[:-5] if file.endswith('.yaml') else file[:-4]
                with open(path, encoding='utf8') as f:
                    translation_mapping = ruamel.yaml.YAML().load(f)
            if lang is not None and translation_mapping is not None:
                self.server.register_translation(lang, {self.translation_prefix: translation_mapping})
                self.logger.debug(f'Registered translation: {file} for scheme {self.get_name()}')

    def on_refresh(self):
        self.server.reload_plugin(self.server.get_self_metadata().id)

    def register_event_listener(self):
        self.server.register_event_listener(MCDRPluginEvents.PLUGIN_UNLOADED, lambda server: self.__inst.scheme_manager.unregister_scheme(self))


def register_scheme(server: PluginServerInterface):
    def deco(cls: Type['AbstractJoinMOTDScheme']):
        plugin_inst = AdvancedJoinMOTD.get_instance()
        manager = plugin_inst.scheme_manager
        if issubclass(cls, AbstractJoinMOTDScheme):
            scheme_inst = manager.register_scheme(cls, server)
            if scheme_inst is None:
                return
            scheme_inst.register_translations()
            scheme_inst.register_event_listener()
        else:
            plugin_inst.logger.error(f"Decorated object is not a subclass of AbstractJoinMOTDScheme: {cls.__name__}")
        return cls
    return deco
