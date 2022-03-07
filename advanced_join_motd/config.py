import json
import os
import time
import requests

from datetime import datetime
from mcdreforged.api.utils import Serializable
from mcdreforged.api.rtext import *
from mcdreforged.api.types import CommandSource, PluginServerInterface
from mcdreforged.api.decorator import new_thread
from typing import *
from ruamel import yaml
from parse import parse
from itertools import groupby
from copy import copy

from advanced_join_motd.random_pools import random_text_manager
from .utils import get_default_motd_file_name, CONFIG_PATH, SCHEME_FOLDER, tr, gl_server, logger, get_self_version

additional_settings: Optional['AdditionalSettings'] = None


class SpecialParameter:
    def __init__(self, **kwargs):
        self.data = kwargs

    @new_thread("AdvJoinMOTD_GetParameters")
    def refresh(self):
        if gl_server is not None:
            api = gl_server.get_plugin_instance('minecraft_data_api')
            self.data = dict(
                day=str(get_day(gl_server)),
                mcdr_version=str(gl_server.get_plugin_metadata('mcdreforged').version),
                minecraft_version=str(gl_server.get_server_information().version),
                player_list='' if api is None else ', '.join(api.get_server_player_list()[2]),
                this_plugin_version=str(get_self_version()[0])
            )
        else:
            self.data = dict()


special_paras = SpecialParameter()


class Schedule(Serializable):
    file: str = get_default_motd_file_name()  # File name in config/advanced_join_motd/motds
    year: Optional[int] = None  # If time match the value display
    mon: Optional[int] = None  # 1~12
    mday: Optional[int] = None  # 1~31
    hour: Optional[int] = None  # 0~23
    min: Optional[int] = None  # 0~59
    secs: Optional[int] = None  # 0~61 With Leap second (60, 61)
    wday: Optional[int] = None  # 0-6
    yday: Optional[int] = None  # 1~366 with Leap day (366 - 2.29)
    from_time: Optional[int] = None  # Unix timestamp
    to_time: Optional[int] = None  # If from_time is larger than to_time no ex
    player_whitelist: Optional[List[str]] = None
    player_blacklist: Optional[List[str]] = None
    priority: int = 1000  # If schedule has same the priority, then sort by the file name

    def __lt__(self, other: 'Schedule'):
        if int(self.priority) != int(other.priority):
            return self.priority < other.priority
        other_data = other.serialize()
        for key, value in self.serialize().items():
            self_value = 0 if value is None else value
            other_value = 0 if other_data[key] is None else other_data[key]
            if self_value != other_value:
                return self_value < other_value
        return False

    def __eq__(self, other):
        return not self < other and not other < self

    def __le__(self, other):
        return self == other or self < other

    @property
    def file_name(self):
        return self.file if self.file.endswith('.yml') else f'{self.file}.yml'

    @property
    def time(self) -> dict:
        rt = {}
        for key, value in self.serialize().items():
            if key in ('year', 'mon', 'mday', 'hour', 'min', 'secs', 'yday', 'wday') and value is not None:
                rt[key] = value
        return rt

    def is_matched(self, player: Optional[str] = None, timestamp: Optional[int] = None):
        timestamp = time.time() if timestamp is None else timestamp
        tm = time.localtime(timestamp)
        if player is not None and bool(
                bool(
                    self.player_blacklist is not None and player in self.player_blacklist
                ) or bool(
                    self.player_whitelist is not None and player not in self.player_whitelist
                )
        ):
            return False
        if self.from_time is not None and self.from_time > timestamp:
            return False
        if self.to_time is not None and self.to_time < self.to_time:
            return False
        is_empty = all((self.from_time is None, self.to_time is None, self.player_whitelist is None,
                        self.player_blacklist is None))
        for key, value in self.time.items():
            is_empty = is_empty and value is None
            if getattr(tm, f'tm_{key}') != value and value is not None:
                return False
        return False if is_empty else True


class RTextVariable(Serializable):
    text: str = ''
    include_special_variables: bool = False
    random_text_pool: Optional[str] = None
    api: Optional[str] = None
    api_json_path: Optional[str] = None
    translate: Optional[str] = None
    mcdr_translate: Optional[str] = None
    color: Optional[RColor] = None
    styles: Optional[Union[RStyle, List[RStyle]]] = None
    hover: Optional[Union[str, 'RTextVariable']] = None
    click_action: Optional[RAction] = None
    click_value: Optional[str] = None

    @property
    def api_json_keys(self) -> tuple:
        keys, rue, num = list(self.api_json_path.split('/')), [], 0
        for l in [list(g) for k, g in groupby(keys, lambda x: x == '') if not k]:
            if len(rue) != 0:
                rue[-1] = rue[-1] + '/' + l.pop()
            rue += l
        return tuple(rue)

    @property
    def api_text(self) -> str:
        try:
            ret = requests.get(self.api, timeout=config.timeout)
            logger.debug(ret.text)
        except:
            return ''
        else:
            if self.api_json_path is not None:
                data, keys = ret.json(), list(self.api_json_keys)
                debug_keys = copy(keys)
                logger.debug(data)
                while True:
                    try:
                        this_key = keys.pop(0)
                    except IndexError:
                        break
                    data = data.get(this_key)
                    if data is None:
                        logger.debug(f'[{this_key}|01] Path error: return full text: {str(debug_keys)}')
                        return ret.text
                    if not isinstance(data, dict):
                        logger.debug(f'[{this_key}|02] No further path: return full text: {str(debug_keys)}')
                        return str(data)
                logger.debug('Path correct: return value')
                return str(data)
            else:
                logger.debug('No path given: return full text')
                return ret.text

    @property
    def rtext(self) -> Union[RText, RTextTranslation, RTextMCDRTranslation]:
        def process(text: str):
            if self.include_special_variables:
                return RText.format(text, **special_paras.data).to_plain_text()
            else:
                return text

        def trans(key: str, with_prefix: bool = True):
            try:
                if self.include_special_variables:
                    ret = tr(key, with_prefix=with_prefix, **special_paras.data)
                else:
                    ret = tr(key, with_prefix=with_prefix)
            except (ValueError, KeyError):
                return None
            if self.color is not None:
                ret.set_color(self.color)
            if self.styles is not None:
                ret.set_styles(self.styles)
            return ret

        rt = None
        try:
            if self.api is not None:
                rt = RText(process(self.api_text), self.color, self.styles)
            else:
                raise RuntimeError
        except:
            random_text = random_text_manager.random(self.random_text_pool)
            if random_text is not None:
                if random_text.startswith(f"{gl_server.get_self_metadata().id}."):
                    rt = trans(random_text)
                else:
                    rt = RText(process(random_text), self.color, self.styles)
            if self.mcdr_translate is not None and rt is None:
                rt = trans(self.mcdr_translate, with_prefix=False)
            if self.translate is not None and rt is None:
                rt = RTextTranslation(self.translate, self.color, self.styles)
            if rt is None:
                if self.text.startswith(f"{gl_server.get_self_metadata().id}."):
                    rt = trans(self.text)
                else:
                    rt = RText(process(self.text), self.color, self.styles)
        if self.hover is not None:
            rt.h(self.hover.rtext)
        logger.debug(f'ClickEvent: {str(self.click_action)} Value: {str(self.click_value)}')
        if self.click_action is not None and self.click_value is not None:
            logger.debug(f'Applied ClickEvent {str(self.click_action)} with value {str(self.click_value)}')
            rt.c(self.click_action, self.click_value)
        return rt


class JoinMOTDScheme(Serializable):
    format: Any = '''
§7=======§r Welcome back to §e{server_name}§7 =======§r
Today is the §e{day}§r day of §e{main_server_name}§r
§7-------§r Server List §7-------§r
{server_list}'''.strip()
    variables: Optional[Dict[str, Union[str, RTextVariable, List[Union[RTextVariable, str]]]]] = {}
    server_list_inherit_global: bool = True
    additional_server_list: Optional[List[str]] = []
    server_list_format: str = '[§7{server}§r]'

    @property
    def formatter(self):
        return str(self.format)

    @property
    def server_list(self):
        server_list = []
        if isinstance(config.server_list, list) and self.server_list_inherit_global:
            server_list += config.server_list
        if isinstance(self.additional_server_list, list):
            server_list += self.additional_server_list
        ret = {}
        for server in server_list:
            psd = parse('[{server_name}]({actual_server_name})', server)
            if psd is not None:
                ret[psd['actual_server_name']] = psd['server_name']
            else:
                ret[server] = server
        logger.debug(f'Server list: {str(ret)}')
        return ret

    @property
    def actual_variables(self):
        ret = config.global_variables
        if self.variables is not None:
            ret.update(self.variables)
        return ret

    @property
    def variables_texts(self):
        texts = {}
        logger.debug(self.actual_variables.items())
        for key, value in self.actual_variables.items():
            if isinstance(value, RTextVariable):
                texts[key] = value.rtext
            elif isinstance(value, list):
                texts[key] = self.process_rtextlist(value)
            else:
                texts[key] = str(value)
        return texts

    @property
    def server_list_text(self):
        text = list()
        for aser, ser in self.server_list.items():
            text.append(
                RText(
                    self.server_list_format.format(server=ser)
                ).c(
                    RAction.run_command, '/server {server}'.format(server=aser)
                ).h(
                    tr('click.jump_server', server=aser)
                )
            )
        return RText.join(' ', text)

    @classmethod
    def process_rtextlist(cls, rtlist: List[Union[str, RTextVariable, list]]):
        rt = RTextList()
        for item in rtlist:
            if isinstance(item, RTextVariable):
                rt.append(item.rtext)
            elif isinstance(item, list):
                rt.append(cls.process_rtextlist(rtlist))
            else:
                rt.append(str(item))
        return rt

    @classmethod
    def init_default(cls, file_name: Optional[str] = None, src: Optional[CommandSource] = None):
        file_name = get_default_motd_file_name() if file_name is None else file_name
        file_name += '.yml' if not file_name.endswith('.yml') else ''
        with open(os.path.join(SCHEME_FOLDER, file_name), 'w', encoding='UTF-8') as f:
            yaml.round_trip_dump(cls.get_default().serialize(), f, allow_unicode=True)
        if isinstance(src, CommandSource):
            src.reply(tr('msg.motd_gen'))
        else:
            logger.info(tr('msg.motd_gen'))

    @property
    def text(self):
        special_paras.refresh().join()
        var = self.variables_texts.copy()
        var.update(special_paras.data)
        var.update(dict(server_list=self.server_list_text))
        logger.debug(var)
        if self.formatter.strip().startswith(f'{gl_server.get_self_metadata().id}.'):
            return tr(self.formatter.strip(), **var)
        else:
            return RTextBase.format(self.formatter.strip(), **var)

    @classmethod
    def load(cls, file_name: str):
        with open(os.path.join(SCHEME_FOLDER, file_name), 'r', encoding='UTF-8') as f:
            return cls.deserialize(dict(yaml.YAML().load(f)))


class AdditionalSettings(Serializable):
    server_list: List[str] = []
    variables: Dict[str, Union[str, RTextVariable, List[Union[RTextVariable, str]]]] = {}

    @classmethod
    def load(cls, file_path: str):
        if file_path is not None and os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='UTF-8') as f:
                    return cls.deserialize(yaml.round_trip_load(f))
            except:
                return None
        else:
            return None


class Config(Serializable):
    command_prefix: Union[List[str], str] = ['!!ajm', '!!joinMOTD']
    variables: Dict[str, Union[str, RTextVariable, List[Union[RTextVariable, str]]]] = {
        'server_name': 'Survival Server',
        'main_server_name': 'My Server'
    }
    default_scheme: str = 'default.yml'
    additional_config: Optional[str] = None
    schedule: Optional[List[Schedule]] = None
    timeout: int = 10
    start_day: Optional[str] = None
    administrator_permission: int = 4
    daycount_plugin_ids: List[str] = [
        'mcd_daycount',
        'day_count_reforged',
        'daycount_nbt'
    ]

    @property
    def default_scheme_name(self):
        if not self.default_scheme.endswith('.yml'):
            return f"{self.default_scheme}.yml"
        return self.default_scheme

    @property
    def all_schedules(self):
        return [] if self.schedule is None else self.schedule

    @property
    def prefix(self):
        return set(self.command_prefix)

    @property
    def server_list(self):
        if self.extra_config is not None:
            return self.extra_config.server_list

    def allowed(self, src: CommandSource):
        return src.has_permission(self.administrator_permission) if src.is_player else src.is_console

    @classmethod
    def load(cls, file_path: str) -> 'Config':
        def log(tr_key: str, *args, **kwargs):
            if gl_server is not None:
                return logger.info(gl_server.rtr(tr_key, *args, kwargs))

        # file existence check
        if not os.path.isfile(file_path):
            default = cls.get_default()
            default.save(file_path=file_path)
            log('server_interface.load_config_simple.failed', 'File is not found')
            return default

        # load
        needs_save = False
        try:
            with open(file_path, 'r', encoding='UTF-8') as f:
                raw_ret = yaml.round_trip_load(f)
                cls.deserialize(raw_ret)
        except Exception as e:
            needs_save, ret = True, cls.get_default()
            log('server_interface.load_config_simple.failed', e)
        else:
            # key check
            for key, value in cls.get_default().serialize().items():
                if key not in raw_ret:
                    raw_ret[key], needs_save = value, True
                    log('server_interface.load_config_simple.key_missed', key, value)
            ret = cls.deserialize(raw_ret)

        # save file
        if needs_save:
            ret.save()
        log('server_interface.load_config_simple.succeed')
        return ret

    @property
    def global_variables(self):
        ret = self.extra_config.variables.copy() if self.extra_config is not None else {}
        ret.update(self.variables)
        return ret

    def save(self, file_path: Optional[str] = None, keep_fmt=True):
        file_path = CONFIG_PATH if file_path is None else file_path
        to_save = self.serialize()
        if os.path.isfile(file_path) and keep_fmt:
            with open(file_path, 'r', encoding='UTF-8') as f:
                fmt = yaml.round_trip_load(f)
                try:
                    self.deserialize(fmt)
                except:
                    pass
                else:
                    fmt.update(to_save)
                    to_save = fmt
        with open(file_path, 'w', encoding='UTF-8') as f:
            logger.debug(to_save)
            yaml.round_trip_dump(to_save, f, allow_unicode=True)

    def init_schedule(self, src: Optional[CommandSource] = None, file_path: Optional[str] = None):
        self.all_schedules.append(Schedule.get_default())
        logger.debug(str(self.serialize()))
        self.save(file_path=file_path)
        if isinstance(src, CommandSource):
            src.reply(tr('msg.sche_gen'))
        else:
            logger.info(tr('msg.sche_gen'))

    @property
    def extra_config(self):
        global additional_settings
        if additional_settings is None:
            additional_settings = AdditionalSettings.load(self.additional_config)
        return additional_settings

    def get_matched_schedules(self, player: Optional[str] = None, reverse: bool = False) -> List[Schedule]:
        ret = []
        for motd in self.all_schedules:
            if motd.is_matched(player):
                ret.append(motd)
        return sorted(ret, reverse=reverse)


config = Config.load(CONFIG_PATH)


def get_day(server: PluginServerInterface) -> str:
    try:
        return str((datetime.now() - datetime.strptime(config.start_day, '%Y-%m-%d')).days)
    except:
        pass
    for pid in set(config.daycount_plugin_ids + ['daycount']):
        api = server.get_plugin_instance(pid)
        if hasattr(api, 'getday') and callable(api.getday):
            return api.getday()
