from mcdreforged.api.types import ServerInterface, PluginServerInterface
from typing import Optional, TYPE_CHECKING

from advanced_join_motd.config import Configuration
from advanced_join_motd.commands import CommandManager
from advanced_join_motd.scheme_manager import SchemeManager
from advanced_join_motd.utils.logger import BlossomLogger
from advanced_join_motd.utils.translation import rtr


if TYPE_CHECKING:
    from advanced_join_motd.api import AbstractJoinMOTDScheme
    from typing import Self


class AdvancedJoinMOTD:
    __instance: Optional["Self"] = None

    def __init__(self):
        self.server = ServerInterface.psi()
        # self.server = ServerInterface.psi_opt()  # psi_opt() if requires to be run standalone
        self.__verbosity = False
        # self.translator = BlossomTranslator(self)
        # self.translator.register_bundled_translations()
        self.logger = BlossomLogger(self)
        self.logger.blossom_bind_single_file()
        self.config = Configuration.load(self)

        self.scheme_manager = SchemeManager(self)
        self.command_manager = CommandManager(self)

    @property
    def verbosity(self):
        return self.__verbosity

    def get_data_folder(self):
        return self.server.get_data_folder()

    def set_verbose(self, verbosity: bool):
        self.__verbosity = verbosity
        if self.__verbosity:
            self.logger.debug("Verbose mode enabled")

    def on_load(self, server: PluginServerInterface, prev_module):
        server.register_help_message(self.config.primary_prefix, rtr('help.mcdr'))
        self.logger.register_event_listeners()
        self.scheme_manager.on_load(server)
        self.command_manager.register_command()

    @classmethod
    def get_instance(cls) -> "Self":
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    """
    # Only MCDR plugin, turn into ABC
    def open_bundled_file(self, file_path: str) -> 'IO[bytes]':
        raise NotImplementedError

    def get_package_path(self):
        raise NotImplementedError
    """
