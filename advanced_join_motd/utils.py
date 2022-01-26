import logging
import os
import time

from mcdreforged.api.all import ServerInterface, RTextMCDRTranslation, MCDReforgedLogger
from datetime import datetime
from typing import Union


VERBOSE = False
gl_server = None if ServerInterface.get_instance() is None else ServerInterface.get_instance().as_plugin_server_interface()
ajm_folder = gl_server.get_data_folder() if gl_server is not None else ''
motd_folder = os.path.join(ajm_folder, 'motds')
tr_folder = os.path.join(ajm_folder, 'translation')
config_path = os.path.join(ajm_folder, 'config.yml')
log_path = os.path.join(ajm_folder, 'ajm.log')
random_text_path = os.path.join(ajm_folder, 'random_text.yml')


class DebugLogger(MCDReforgedLogger):
    DEFAULT_NAME = 'AdvJoinMOTD'

    def debug(self, *args):
        if VERBOSE:
            super(MCDReforgedLogger, self).debug(*args)

    def set_file(self, file_name):
        if self.file_handler is not None:
            self.removeHandler(self.file_handler)
        self.file_handler = logging.FileHandler(file_name, encoding='UTF-8')
        self.file_handler.setFormatter(self.FILE_FMT)
        self.addHandler(self.file_handler)
        return self


logger = DebugLogger()


class AdvancedInteger:
    def __init__(self, value: int):
        self.value = value

    @property
    def digits_list(self):
        return [int(num) for num in list(str(self.value))]

    def __len__(self):
        return len(self.digits_list)

    def __getitem__(self, item: Union[str, int, float]):
        ind = int(item)
        return 0 if (ind >= 0 and ind + 1 > len(self)) or (ind < 0 and abs(ind) > len(self)) else self.digits_list[ind]

    @property
    def ordinal(self) -> str:
        if self[-2] == 1:
            return f'{self.value}th'
        elif self[-1] not in (1, 2, 3):
            return f'{self.value}th'
        elif self[-1] == 1:
            return f'{self.value}st'
        elif self[-1] == 2:
            return f'{self.value}nd'
        elif self[-1] == 3:
            return f'{self.value}rd'
        else:
            return ''

    def __str__(self):
        return str(self.value)


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
    if not os.path.isdir(motd_folder):
        os.makedirs(motd_folder)
    file_list = os.listdir(motd_folder)
    fmt = 'new_motd{}.yml'
    if fmt.format('') not in file_list:
        return fmt.format('')
    num = 1
    while True:
        if fmt.format(f'_{str(num)}') not in file_list:
            return fmt.format(f'_{str(num)}')
