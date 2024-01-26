import functools
import inspect
import sys
import threading
from io import StringIO
from typing import Optional, Callable, Union

from mcdreforged.api.decorator import FunctionThread
from mcdreforged.api.types import ServerInterface
from ruamel import yaml

psi = ServerInterface.psi_opt()


def get_thread_prefix() -> str:
    return to_camel_case(psi.get_self_metadata().name, divider='_') + '_'


def named_thread(arg: Optional[Union[str, Callable]] = None) -> Callable:
    def wrapper(func):
        @functools.wraps(func)
        def wrap(*args, **kwargs):
            def try_func():
                try:
                    return func(*args, **kwargs)
                finally:
                    if sys.exc_info()[0] is not None:
                        psi.logger.exception('Error running thread {}'.format(threading.current_thread().name))

            prefix = get_thread_prefix()
            thread = FunctionThread(target=try_func, args=[], kwargs={}, name=prefix + thread_name)
            thread.start()
            return thread

        wrap.__signature__ = inspect.signature(func)
        wrap.original = func
        return wrap

    # Directly use @new_thread without ending brackets case, e.g. @new_thread
    if isinstance(arg, Callable):
        thread_name = to_camel_case(arg.__name__, divider="_")
        return wrapper(arg)
    # Use @new_thread with ending brackets case, e.g. @new_thread('A'), @new_thread()
    else:
        thread_name = arg
        return wrapper


def to_camel_case(string: str, divider: str = ' ', upper: bool = True) -> str:
    word_list = [capitalize(item) for item in string.split(divider)]
    if not upper:
        first_word_char_list = list(word_list[0])
        first_word_char_list[0] = first_word_char_list[0].lower()
        word_list[0] = ''.join(first_word_char_list)
    return ''.join(word_list)


def capitalize(string: str) -> str:
    if string == '':
        return ''
    char_list = list(string)
    char_list[0] = char_list[0].upper()
    return ''.join(char_list)


def yaml_dump_to_string(data: Union[dict, list], yaml_inst: Optional[yaml.YAML] = None):
    if yaml_inst is None:
        yaml_inst = yaml.YAML(typ='rt')
        yaml_inst.width = 1048576
    with StringIO() as stream:
        yaml_inst.dump(data, stream)
        stream.seek(0)
        return stream.read()
