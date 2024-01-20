import logging
import os
import re
from typing import Optional, TYPE_CHECKING

from mcdreforged.api.event import MCDRPluginEvents
from mcdreforged.api.types import MCDReforgedLogger

from advanced_join_motd.utils.file_util import ensure_dir

if TYPE_CHECKING:
    from advanced_join_motd.advanced_join_motd import AdvancedJoinMOTD


class BlossomLogger(MCDReforgedLogger):
    class NoColorFormatter(logging.Formatter):
        def formatMessage(self, record) -> str:
            return self.clean_console_color_code(self.clean_minecraft_color_code(super().formatMessage(record)))

        @staticmethod
        def clean_console_color_code(text: str) -> str:
            return re.compile(r'\033\[(\d+(;\d+)?)?m').sub('', text)

        @staticmethod
        def clean_minecraft_color_code(text: str):
            return re.compile(r'§[a-z0-9]').sub('', str(text))

    __SINGLE_FILE_LOG_PATH: Optional[str] = "alocasia.log"
    FILE_FMT: NoColorFormatter = NoColorFormatter(
        '[%(name)s] [%(asctime)s] [%(threadName)s/%(levelname)s]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    def __init__(self, plugin_inst: "AdvancedJoinMOTD"):
        self.__inst = plugin_inst
        psi = self.__inst.server
        self._blossom_file_handler = None
        if psi is not None:
            super().__init__(psi.get_self_metadata().id)
        else:
            super().__init__()

    def debug(self, *args, option=None, no_check: bool = False) -> None:
        return super().debug(*args, option=option, no_check=no_check or self.__inst.verbosity)

    def _blossom_unbind_file(self, *args, **kwargs) -> None:
        if self._blossom_file_handler is not None:
            self.removeHandler(self._blossom_file_handler)
            self._blossom_file_handler.close()
            self._blossom_file_handler = None

    def blossom_bind_single_file(self, file_name: Optional[str] = None) -> "BlossomLogger":
        if file_name is None:
            if self.__SINGLE_FILE_LOG_PATH is None:
                return self
            file_name = os.path.join(self.__inst.get_data_folder(), self.__SINGLE_FILE_LOG_PATH)
        self._blossom_unbind_file()
        ensure_dir(os.path.dirname(file_name))
        self._blossom_file_handler = logging.FileHandler(file_name, encoding='UTF-8')
        self._blossom_file_handler.setFormatter(self.FILE_FMT)
        self.addHandler(self._blossom_file_handler)
        return self

    def register_event_listeners(self):
        self.__inst.server.register_event_listener(MCDRPluginEvents.PLUGIN_LOADED, self._blossom_unbind_file)
