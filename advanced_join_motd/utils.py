from mcdreforged.api.all import ServerInterface, RTextMCDRTranslation, MCDReforgedLogger
from datetime import datetime
import logging
import os
import time


VERBOSE = True
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
