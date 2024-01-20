import contextlib
import enum
import os
import shutil
from typing import ContextManager, TextIO

from mcdreforged.api.types import ServerInterface

psi = ServerInterface.psi_opt()


class LineBreak(enum.Enum):
    LF = '\n'
    CRLF = '\r\n'
    CR = '\r'


def delete(target_file_path: str):
    if os.path.isfile(target_file_path):
        os.remove(target_file_path)
    elif os.path.isdir(target_file_path):
        shutil.rmtree(target_file_path)


@contextlib.contextmanager
def safe_write(target_file_path: str, *, encoding: str = 'utf8') -> ContextManager[TextIO]:
    temp_file_path = target_file_path + '.tmp'
    delete(temp_file_path)
    with open(temp_file_path, 'w', encoding=encoding) as file:
        yield file
    os.replace(temp_file_path, target_file_path)


def lf_read(target_file_path: str, *, is_bundled: bool = False, encoding: str = 'utf8') -> str:
    if is_bundled:
        with psi.open_bundled_file(target_file_path) as f:
            file_string = f.read()
    else:
        with open(target_file_path, 'r', encoding=encoding) as f:
            file_string = f.read()
    return file_string.replace(LineBreak.CRLF.value, LineBreak.LF.value).replace(LineBreak.CR.value, LineBreak.LF.value)


def ensure_dir(folder: str):
    if os.path.isfile(folder):
        raise FileExistsError('Data folder structure is occupied by existing file')
    if not os.path.isdir(folder):
        os.makedirs(folder)
    return folder
