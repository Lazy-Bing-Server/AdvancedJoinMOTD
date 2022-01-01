import os
import time, datetime

from mcdreforged.api.utils import Serializable
from mcdreforged.api.rtext import *
from mcdreforged.api.types import CommandSource
from typing import *
from ruamel import yaml
from parse import parse
from urllib.request import urlopen

from minecraft_data_api import get_server_player_list
from .utils import get_default_motd_file_name, config_path, motd_folder, tr, gl_server, logger


# TODO: JoinMOTD Whitelist


class Schedule(Serializable):
    file: str = get_default_motd_file_name()  # File name in config/advanced_join_motd/motds
    year: Optional[int] = None                # If time match the value display
    mon: Optional[int] = None                 # 1~12
    mday: Optional[int] = None                # 1~31
    hour: Optional[int] = None                # 0~23
    min: Optional[int] = None                 # 0~59
    secs: Optional[int] = None                # 0~61 With Leap second (60, 61)
    wday: Optional[int] = None                # 0-6
    yday: Optional[int] = None                # 1~366 with Leap day (366 - 2.29)
    from_time: Optional[int] = None           # Unix timestamp
    to_time: Optional[int] = None             # If from_time is larger than to_time no ex
    priority: int = 1000                      # If schedule has same the priority, then sort by the file name

    def __lt__(self, other: 'Schedule'):
        if int(self.priority) != int(other.priority):
            return self.priority > other.priority
        other_data = other.serialize()
        for key, value in self.serialize().items():
            if value != other_data[key]:
                return 0 if value is None else value > 0 if other_data[key] is None else other_data[key]
        return False

    def __eq__(self, other):
        return not self < other and not other < self

    def __le__(self, other):
        return self == other or self < other

    @property
    def time(self) -> dict:
        rt = {}
        for key, value in self.serialize().items():
            if key in ('year', 'mon', 'mday', 'hour', 'min', 'secs', 'yday', 'wday') and value is not None:
                rt[key] = value
        return rt

    def is_matched(self, timestamp: Optional[int] = None):
        timestamp = time.time() if timestamp is None else timestamp
        tm = time.localtime(timestamp)._asdict()
        if self.from_time > timestamp or self.to_time < self.to_time:
            return False
        is_empty = self.from_time is None and self.to_time is None
        for key, value in self.time.items():
            is_empty = is_empty and value is None
            if tm[f'tm_{key}'] != value and value is not None:
                return False
        return False if is_empty else True

    @property
    def motd(self):
        return JoinMOTD.load(self.file)


class RTextVariable(Serializable):
    text: str = ''
    api: Optional[str] = None
    translate: Optional[str] = None
    mcdr_translate: Optional[str] = None
    color: Optional[RColor] = None
    styles: Optional[Union[RStyle, List[RStyle]]] = None
    hover: Optional[Union[str, 'RTextVariable']] = None
    click_action: Optional[RAction] = None
    click_value: Optional[str] = None

    @property
    def api_text(self) -> str:
        ret = urlopen(self.api, timeout=config.timeout)
        if hasattr(ret, 'read') and callable(ret.read) and ret.read() is not None:
            return ret.read().decode('utf8').strip()
        else:
            return ''

    @property
    def rtext(self) -> Union[RText, RTextTranslation, RTextMCDRTranslation]:
        try:
            if self.api is not None:
                rt = RText(self.api_text.format(**special_parameters), self.color, self.styles)
            else:
                raise RuntimeError
        except:
            if self.mcdr_translate is not None:
                rt = tr(self.mcdr_translate, **special_parameters)
                if self.color is not None:
                    rt.set_color(self.color)
                if self.styles is not None:
                    rt.set_styles(self.styles)
            elif self.translate is not None:
                rt = RTextTranslation(self.translate, self.color, self.styles)
            else:
                rt = RText(self.text.format(**special_parameters), self.color, self.styles)
        if self.hover is not None:
            rt.h(self.hover)
        if self.click_action is not None and self.click_value is not None:
            rt.c(self.click_action, self.click_value)
        return rt


class JoinMOTD(Serializable):
    format: str = ''
    variables: Dict[str, Union[str, RTextVariable, List[Union[RTextVariable, str]]]] = {}
    server_list_inherit_global: bool = True
    daycount: Optional[str] = None
    additional_server_list: Optional[List] = []
    server_list_format: str = '[§7{server}§r]'

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
        return ret

    @property
    def actual_variables(self):
        ret = config.global_variables
        ret.update(self.variables)
        return ret

    @property
    def variables_texts(self):
        texts = {}
        for key, value in self.actual_variables.items():
            texts[key] = value.rtext if isinstance(value, RTextVariable) else str(value)
        return texts

    @property
    def server_list_text(self):
        text = list()
        for ser, aser in self.server_list.items():
            text.append(
                RText(
                    self.server_list_format.format(server=ser)
                ).c(
                    RAction.run_command, 'server {server}'.format(server=aser)
                ).h(
                    tr('click.jump_server', server=aser)
                )
            )
        return RText.join(' ', text)

    @classmethod
    def init_default(cls, file_name: Optional[str] = None, src: Optional[CommandSource] = None):
        file_name = get_default_motd_file_name() if file_name is None else file_name
        file_name += '.yml' if not file_name.endswith('.yml') else ''
        with open(os.path.join(motd_folder, file_name), 'w', encoding='UTF-8') as f:
            yaml.round_trip_dump(cls.get_default(), f, allow_unicode=True)
        if isinstance(src, CommandSource):
            src.reply(tr('msg.motd_gen'))
        else:
            logger.info(tr('msg.motd_gen'))

    @property
    def text(self):
        return RText.format(
            self.format,
            server_list=self.server_list_text,
            **self.variables_texts
        )

    @classmethod
    def load(cls, file_name: str):
        with open(os.path.join(motd_folder, file_name), 'r', encoding='UTF-8') as f:
            return cls.deserialize(yaml.round_trip_load(f))


class AdditionalSettings(Serializable):
    server_list: List[str] = []
    variables: Dict[str] = {}


class Config(Serializable):
    prefix: Union[List[str], str] = ['!!ajm', '!!joinMOTD']
    variables: Dict[str, Union[str, RTextVariable, List[Union[RTextVariable, str]]]] = {
        'server_name': 'Survival Server',
        'main_server_name': 'My Server'
    }
    default_motd: str = 'default.yml'
    additional_config: Optional[str] = None
    schedule: List[Schedule] = []
    timeout: int = 2
    start_day: Optional[str] = None
    administrator_permission: int = 4
    daycount_plugin_ids: List[str] = [
        'mcd_daycount',
        'day_count_reforged',
        'daycount_nbt'
    ]
    @property
    def server_list(self):
        if self.extra_config is not None:
            return self.extra_config.server_list

    def allowed(self, src: CommandSource):
        return src.has_permission(self.administrator_permission) if src.is_player else src.is_console

    @classmethod
    def load(cls, file_path: str) -> 'Config':
        with open(file_path, 'r', encoding='UTF-8') as f:
            return cls.deserialize(yaml.round_trip_load(f))

    @property
    def global_variables(self):
        ret = self.extra_config.variables.copy() if self.extra_config is not None else {}
        ret.update(self.variables)
        return ret

    def save(self):
        with open(config_path, 'w', encoding='UTF-8') as f:
            yaml.round_trip_dump(self.serialize(), f, allow_unicode=True)

    def init_schedule(self, src: Optional[CommandSource] = None):
        self.schedule.append(Schedule.get_default())
        self.save()
        if isinstance(src, CommandSource):
            src.reply(tr('msg.sche_gen'))
        else:
            logger.info(tr('msg.sche_gen'))

    @property
    def extra_config(self):
        if os.path.isfile(self.additional_config):
            try:
                with open(self.additional_config, 'r', encoding='UTF-8') as f:
                    return AdditionalSettings.deserialize(yaml.round_trip_load(f))
            except:
                return None
        return None

    def get_current_join_motd(self):
        ret = []
        for motd in self.schedule:
            if motd.is_matched():
                ret.append(motd)
        return [item.motd for item in sorted(ret, reverse=True)]


config = Config.load(config_path)


def get_day() -> str:
    """
    Copied from JoinMOTD
    """
    try:
        startday = datetime.datetime.strptime(config.start_day, '%Y-%m-%d')
        now = datetime.datetime.now()
        output = now - startday
        return str(output.days)
    except:
        pass
    for pid in config.daycount_plugin_ids:
        api = gl_server.get_plugin_instance(pid)
        if hasattr(api, 'getday') and callable(api.getday):
            return api.getday()
    try:
        import daycount
        return daycount.getday()
    except:
        return '?'


special_parameters = dict(
    day=get_day(), mcdr_version=str(gl_server.get_plugin_metadata('mcdreforged').version),
    minecraft_version=str(gl_server.get_server_information().version),
    player_list=get_server_player_list(), this_plugin_version=str(gl_server.get_self_metadata().version)
)
