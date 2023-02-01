import logging
import os
import re
import time

from mcdreforged.api.all import ServerInterface, RTextMCDRTranslation, MCDReforgedLogger
from datetime import datetime
from typing import Tuple


VERBOSE = True
__server = ServerInterface.get_instance()
gl_server = None if __server is None else __server.as_plugin_server_interface()
DATA_FOLDER = gl_server.get_data_folder() if gl_server is not None else ''
SCHEME_FOLDER = os.path.join(DATA_FOLDER, 'schemes')
TRANSLATION_FOLDER = os.path.join(DATA_FOLDER, 'translation')
CONFIG_PATH = os.path.join(DATA_FOLDER, 'config.yml')
LOG_PATH = os.path.join(DATA_FOLDER, 'ajm.log')
RANDOM_TEXT_PATH = os.path.join(DATA_FOLDER, 'random_text.yml')


class NoColorFormatter(logging.Formatter):
    def formatMessage(self, record):
        return clean_console_color_code(super().formatMessage(record))


class DebugLogger(MCDReforgedLogger):
    DEFAULT_NAME = 'AdvJoinMOTD'

    def debug(self, *args):
        if VERBOSE:
            super(MCDReforgedLogger, self).debug(*args)

    def set_file(self, file_name):
        if self.file_handler is not None:
            self.removeHandler(self.file_handler)
        self.file_handler = logging.FileHandler(file_name, encoding='UTF-8')
        self.file_handler.setFormatter(
            NoColorFormatter(
                f'[%(name)s] [%(asctime)s] [%(threadName)s/%(levelname)s]: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
        self.addHandler(self.file_handler)
        return self


logger = DebugLogger()
logger.set_file(LOG_PATH)


def now_dict():
    now_list_raw = now_time().strftime('%S %M %H %d %m %Y %w').split(' ')
    now_list = []
    for element in now_list_raw:
        now_list.append(int(element))
    return time.struct_time(*now_list)


def now_time(unix=False):
    if unix:
        return int(time.mktime(datetime.now().timetuple()))
    return datetime.now()


def tr(key: str, *args, with_prefix: bool = True, **kwargs) -> RTextMCDRTranslation:
    if not key.startswith(gl_server.get_self_metadata().id + '.') and with_prefix:
        key = f'{gl_server.get_self_metadata().id}.{key}'
    return gl_server.rtr(key, *args, **kwargs)


def get_default_motd_file_name():
    if gl_server is None:
        return ''
    if not os.path.isdir(SCHEME_FOLDER):
        os.makedirs(SCHEME_FOLDER)
    file_list = os.listdir(SCHEME_FOLDER)
    fmt = 'new_motd{}.yml'
    if fmt.format('') not in file_list:
        return fmt.format('')
    num = 1
    while True:
        if fmt.format(f'_{str(num)}') not in file_list:
            return fmt.format(f'_{str(num)}')


def get_self_version() -> Tuple[str, int]:
    meta = gl_server.get_self_metadata()
    version = meta.version
    version_str = '.'.join(map(lambda c: str(c) if c != version.WILDCARD else version.WILDCARDS[0], version.component))
    if version.pre is not None:
        version_str += '-' + str(version.pre)
    build = 0 if version.build is None else version.build.num
    return version_str, build


def clean_console_color_code(text):
    return re.sub(r'\033\[(\d+(;\d+)?)?m', '', text)

