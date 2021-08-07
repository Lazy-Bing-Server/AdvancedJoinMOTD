import os
import re
import time
import json
import shutil
import logging
import datetime
import collections

from mcdreforged.api.all import *
from parse import parse
from typing import Optional, Union, List
from urllib.request import urlopen
from zipfile import ZipFile
from ruamel import yaml

try:
    from mcdreforged.constants.core_constant import VERSION as MCDR_VERSION
except ImportError:
    try:
        from mcdreforged.constant import VERSION as MCDR_VERSION
    except ImportError:
        MCDR_VERSION = 'Invalid version'


# 1.x metadata
plg_name = 'Advanced Join MOTD'
plg_id = 'advanced_join_motd'
plg_desc = 'Custom your own join MOTD.'
verbose_mode = True
PLUGIN_METADATA = {
    'id': plg_id,
    'version': '0.6.0-alpha1',
    'name': plg_id,
    'description': plg_desc,
    'author': 'Ra1ny_Yuki',
    'link': 'https://github.com/Lazy-Bing-Server/AdvancedJoinMOTD',
    'dependencies':
    {
        'mcdreforged': '>=1.5.0',
        'daycount': '*'
    }
}

command = '!!joinMOTD'
config_folder, reconfig_path, logger = '', '', None
readme_text = '''
本说明由{0} (插件版本: {1} Version {2})自动生成, 修订时间: 2021-08-07 13:42:00
生成时间: {3}

一. 时间特定的欢迎文本：
默认显示regular.txt内包含的文本
低于snapshot build 3版本(即alpha ver 0.3)的配置文本会被自动移动到regular.txt, 不会覆盖已存在的regular.txt
当需要在特定时间段显示特定欢迎文本时, 请新建文本文件
文件名格式可为如下两种:
其中的任意元素可以替换为~表示未指定, 当该元素为未指定时不同格式会有不同处理原则
1.<秒>_<分>_<时>_<日>_<月>_<年>_<星期几>.txt
    将当前时间与该文件名所表示的时间表达式进行匹配
    当且仅当全部元素匹配成功时显示该文本文件中的文字
    当元素未指定时默认为匹配成功
    星期几的范围为0-6, 0为星期日, 1为星期一, 以此类推
2.<秒>_<分>_<时>_<日>_<月>_<年>;<秒>_<分>_<时>_<日>_<月>_<年>.txt
    将当前时间与该文件名所表示的两个时间点进行比较
    当且仅当目前时间处于两者之间的闭区间中时(无所谓时间)显示该文本文件中的文字
    当秒分时未指定时会被置为0
    当日月年未制定时会被置为当前时间的日月年

二. 转义字符: (转义内容均不可跨行)
可以利用转义字符为其添加各种元素
{4}
附录: Minecraft 字符样式转义代码
{5}'''.strip()

DEFAULT_TEXT = r'''
§7=======§r 欢迎回到 §eMy Server§7 =======§r
今天是 §e?§r 开服的第 §e%day%§r 天
§7-------§r Server List §7-------§r
%serverlist: survival mirror creative%
'''  # Do not change this!!

OLD_TEXT_FILE = 'config/adv_joinmotd.txt'
STYLE_ELEMENTS = {'§4': '绛红', '§c': '鲜红', '§6': '橙', '§e': '黄', '§2': '深绿', '§a': '黄绿',
                  '§b': '浅青', '§3': '青', '§1': '深蓝', '§9': '蓝', '§d': '品红', '§5': '深紫',
                  '§f': '白', '§7': '浅灰', '§8': '灰', '§0': '黑',
                  '§r': '取消样式与颜色', '§l': '加粗', '§o': '斜体', '§n': '下划线', '§m': '删除线', '§k': '混淆'}


class TimeFormat:
    def __init__(self, sec: int, mins: int, hrs: int, date: int, mon: int, yrs: int, day: Optional[int] = None):
        self.__data = {
            'sec': sec, 'min': mins, 'hrs': hrs, 'date': date, 'mon': mon, 'yrs': yrs
        }
        if day is not None:
            self.__data['day'] = day
        self.__dict__.update(self.__data)

    @classmethod
    def make(cls, iters: List[int]):
        if len(iters) in [6, 7]:
            return TimeFormat(*iters)
        else:
            raise TypeError('Length should be 6 or 7')

    def asdict(self):
        return self.__data


class Func:
    def __init__(self, func) -> None:
        self.function = lambda ele: func(ele)
        self.comment = func.__doc__
        if self.comment is None:
            self.comment = ''


class LineFormatter:
    HOVER_ELEMENTS = {'7': '执行', '8': '补全', 'a': '复制', 'n': '访问'}
    CLICK_EVENTS = {
        '7': RAction.run_command, '8': RAction.suggest_command, 'a': RAction.copy_to_clipboard, 'n': RAction.open_url
    }
    pattern = r'%[\S ]*?%'

    def __init__(self, text: str, player: str, server: Optional[ServerInterface] = None):
        self.raw_text = self.__remove_comment(text)
        self.rtext_ori = re.findall(self.pattern, self.raw_text)
        self.normal_text = re.split(self.pattern, self.raw_text)
        self.player = player
        self.server = server

    @staticmethod
    def __remove_comment(imports: str, *args, **kwargs) -> str:
        """
        # 单行注释, #之后的文本将不予显示, 如需在文本中包含#请使用\#代替#
        """
        splitted = imports.split('#')
        ret = ''
        for num in range(len(splitted)):
            if not splitted[num].endswith('\\') or num == len(splitted):
                ret += f'{splitted[num]}'
                break
            else:
                ret += splitted[num][:-1] + '#'
        return ret

    def __get_player(self, imports: str, *args, **kwargs) -> str:
        """
        %player% 上线玩家名称
        """
        return self.player

    def __get_daycount(self, imports: str, *args, **kwargs) -> str:
        """
        %day% 开服时间
        """
        if hasattr(self.server, 'get_plugin_instance'):
            return self.server.get_plugin_instance('daycount').getday()

    @staticmethod
    def __get_day(imports: str, *args, **kwargs) -> str:
        """
        %since: <date>% 自某日开始至今的日期的绝对值, 输入日期应形如yyyy-mm-dd
        """
        output = datetime.datetime.now() - datetime.datetime.strptime(imports[6:].strip(), '%Y-%m-%d')
        return str(abs(output.days))

    @staticmethod
    def __get_serverlist(imports: str, *args, **kwargs) -> Union[RTextBase, str]:
        """
        %serverlist: <servers>% 群组服子服列表, 引号后接子服务器列表<servers>, 使用逗号分隔, 服务器列表不可换行
        """
        server_list = imports[11:].strip().split(',')
        server_text = ''
        for server_ in server_list:
            psd = parse('[{outer}]({inner})', server_.strip())
            outer = psd['outer'] if psd else server_.strip()
            inner = psd['inner'] if psd else server_.strip()
            server_text += rclick(f'[§7{outer}§r]', f'点击跳转到 §7{inner}§r', f'/server {inner}') + ' '
        return server_text

    def __get_playerlist(self, imports: str, *args, **kwargs) -> str:
        """
        %playerlist% 当前全部玩家列表, 需要有效的rcon连接
        """
        raw_rcdata = None
        if hasattr(self.server, 'rcon_query'):
            raw_rcdata = self.server.rcon_query('list')
        if raw_rcdata is not None:
            player_list = str(raw_rcdata).split(' players online:')[1].strip().split(',')
            playerlist = ''
            for player_name in player_list:
                playerlist += ', ' if playerlist != '' else ''
                playerlist += player_name.strip()
            return playerlist
        return imports

    @staticmethod
    def __get_mcdr_version(imports: str, *args, **kwargs) -> str:
        """
        %mcdrVersion% 当前MCDReforged版本
        """
        return MCDR_VERSION

    @staticmethod
    def __get_plugin_version(imports: str, *args, **kwargs) -> str:
        """
        %pluginVersion% 当前Advanced Join MOTD的版本
        """
        return PLUGIN_METADATA['version']

    @staticmethod
    def __get_server_version(imports: str, *args, **kwargs) -> str:
        """
        %version: <server_jar>% 原版服务端的版本, <server_jar>应为MCDR配置文件中填写的工作目录下有效的原版服务端
        """
        try:
            server_path = os.path.join(get_server_folder(), imports[8:].strip())
            with GetServerJSON(server_path):
                with open(os.path.join(get_server_folder(), 'version.json'), 'r', encoding='UTF-8') as f:
                    return json.load(f)['name']
        except FileNotFoundError:
            return imports

    @staticmethod
    def __get_text_from_api(imports: str, *args, **kwargs) -> str:
        """
        %API: <url>% 从API获取文本并显示, 引号后接API地址
        """
        ret = urlopen(imports[4:])
        if hasattr(ret, 'read'):
            return ret.read().decode('utf8').strip() if ret.read() is not None else imports
        else:
            return imports

    @classmethod
    def __get_click_event(cls, imports: str, *args, **kwargs) -> RTextBase:
        """
        %7<text>% 浅灰色字符, 点击可执行包含的指令, <text>处可直接填写完整指令(或对应点击事件的内容), <text>也可填写符合格式[文本](点击事件的指令、复制内容或外部URL)的内容以使显示的文本与点击执行的内容不一致
        %8<text>% 浅灰色字符, 点击补全可执行包含的指令, <text>填写方法同上
        %a<text>% 黄绿色字符, 点击复制到剪贴板, <text>填写方法同上
        %n<text>% 带下划线字符, 点击访问外部URL链接, <text>填写方法同上
        """
        psd = parse('{event}[{name}]({content})', imports)
        pre = psd['event'] if psd else list(imports)
        event = ls.CLICK_EVENTS[psd['event']] if psd else cls.CLICK_EVENTS[list(imports)[0]]
        hover = cls.HOVER_ELEMENTS[psd['event']] if psd else cls.HOVER_ELEMENTS[list(imports)[0]]
        name = psd['name'] if psd else imports[1:]
        content = psd['content'] if psd else clean(imports[1:])
        return rclick(f"§{pre}{name}§r", f"点击{hover} §7{content}§r", content, event)

    @property
    def actions(self):
        actions = {
            'since:': Func(self.__get_day),
            'player': Func(self.__get_player),
            'day': Func(self.__get_daycount),
            'playerlist': Func(self.__get_playerlist),
            'serverlist:': Func(self.__get_serverlist),
            'API:': Func(self.__get_text_from_api),
            'version:': Func(self.__get_server_version),
            'mcdrVersion': Func(self.__get_mcdr_version),
            'pluginVersion': Func(self.__get_plugin_version)
        }
        cle = {}
        for key in self.CLICK_EVENTS.keys():
            cle[key] = Func(self.__get_click_event)
        actions.update(cle)
        return actions

    @property
    def comments(self):
        comment_list = [self.__remove_comment.__doc__.strip()]
        for item in list(self.actions.values())[:-3]:
            il = item.comment.strip().splitlines()
            for i in il:
                comment_list.append(i.strip())
        return comment_list

    @property
    def formatted(self):
        rtext_converted = []
        for e in self.rtext_ori:
            ele = e[1:-1].strip()
            converted_ele = None
            for key, value in self.actions.items():
                if ele.startswith(key):
                    converted_ele = value.function(ele)
            if converted_ele in [None, ele]:
                converted_ele = e
            rtext_converted.append(converted_ele)

        final_line = ''
        for num in range(len(self.normal_text)):
            final_line += str(self.normal_text[num])
            if num + 1 == len(self.normal_text):
                break
            final_line += rtext_converted[num]
        return final_line


class GetServerJSON:
    def __init__(self, server_file: str):
        self.pkg = ZipFile(server_file)
        self.server_folder = os.path.split(server_file)[0]
        self.js = os.path.join(self.server_folder, 'version.json')

    def __enter__(self):
        self.pkg.extract('version.json', self.server_folder)

    def __exit__(self, types, value, stack_info):
        os.remove(self.js)


def get_server_folder():
    with open('config.yml') as f:
        return yaml.round_trip_load(f)['working_directory']


def convert_text(server: ServerInterface, text: str, player) -> Union[RTextBase, str]:
    return_text = ''
    for line in text.splitlines():
        if return_text != '':
            return_text += '\n'
        if not line.startswith('#'):
            formatter = LineFormatter(line, player, server)
            return_text += formatter.formatted
    return return_text


def get_text() -> str:
    text_file = os.path.join(config_folder, choose_file())
    with open(text_file, 'r', encoding='UTF-8') as f:
        text = f.read()
    return text


def now_time(unix=False):
    if unix:
        return int(time.mktime(datetime.datetime.now().timetuple()))
    return datetime.datetime.now()


def nowdict():
    now_list_raw = now_time().strftime('%S %M %H %d %m %Y %w').split(' ')
    now_list = []
    for element in now_list_raw:
        now_list.append(int(element))
    return TimeFormat.make(now_list).asdict()


def is_matched(dt: dict):
    now_dict = nowdict()
    for key, value in dt.items():
        if value == '~':
            value_after = None
        else:
            value_after = int(value)
        logger.debug('{}: 表达式中为{}, 当前为{}'.format(key, value_after, now_dict[key]))
        ret = value_after in [now_dict[key], None]
        logger.debug('{}符合条件'.format('' if ret else '不'))
        if not ret:
            return False
    return True


def to_unix_timestamp(t: TimeFormat):
    logger.debug(time.mktime(time.strptime(f'{t.sec} {t.min} {t.hrs} {t.date} {t.mon} {t.yrs}', '%S %M %H %d %m %Y')))
    return int(time.mktime(time.strptime(f'{t.sec} {t.min} {t.hrs} {t.date} {t.mon} {t.yrs}', '%S %M %H %d %m %Y')))


def is_in_range(from_time: int, to_time: int):
    now_timestamp = now_time(True)
    logger.debug('当前的时间戳为: ' + str(now_timestamp))
    time_list = [from_time, to_time, now_timestamp]
    logger.debug('符合该条件的最小时间为: {} 最大时间为: {}'.format(from_time, to_time))
    if max(time_list) != now_timestamp and min(time_list) != now_timestamp:
        ret = True
    elif now_timestamp == from_time or now_timestamp == to_time:
        ret = True
    else:
        ret = False
    logger.debug('当前时间{}在该范围中'.format('' if ret else '不'))


def convert_from_to(format_from_to: dict):
    formatted_from_to = []
    for key, value in format_from_to.items():
        if value == '~':
            if key.replace('from_', '').replace('to_', '') in ['sec', 'min', 'hrs']:
                formatted_from_to.append(0)
            else:
                formatted_from_to.append(nowdict()[key.replace('from_', '').replace('to_', '')])
        else:
            formatted_from_to.append(int(value))
    from_time, to_time = TimeFormat.make(formatted_from_to[:6]), TimeFormat.make(formatted_from_to[6:])
    return to_unix_timestamp(from_time), to_unix_timestamp(to_time)


def is_current(file_name: str):
    ret = 'regular.txt'
    format_from_to = parse('{from_sec}_{from_min}_{from_hrs}_{from_date}_{from_mon}_{from_yrs};' +
                           '{to_sec}_{to_min}_{to_hrs}_{to_date}_{to_mon}_{to_yrs}.txt', file_name)
    if format_from_to is not None:
        from_time, to_time = convert_from_to(format_from_to.named)
        if is_in_range(from_time, to_time):
            return file_name
        else:
            return ret
    format_series = parse('{sec}_{min}_{hrs}_{date}_{mon}_{yrs}_{day}.txt', file_name)
    if format_series is not None:
        if is_matched(format_series.named):
            ret = file_name
    return ret


def choose_file():
    current_file = 'regular.txt'
    for file in os.listdir(config_folder):
        if file != 'ReadMe.txt' and file != 'regular.txt':
            current_file = is_current(file)
            if current_file != 'regular.txt':
                break
    return current_file


def clean(msg: str):
    for item in STYLE_ELEMENTS.keys():
        msg = msg.replace(item, '')
    return msg


def on_player_joined(server: ServerInterface, player: str, info: Info):
    try:
        text = get_text()
        raw_text = convert_text(server, text, player)
        server.tell(player, raw_text)
        logger.debug(f'玩家{player}加入时的欢迎信息为: \n{raw_text}')
    except Exception as e:
        server.tell(player, f'Advanced Join MOTD出现错误, 请通知管理员处理, 错误如下: \n§c{e}§r')
        logger.exception('AdvancedJoinMOTD出现异常, 错误如下: ')
        raise


def rclick(message: str, hover_text: str, click_content: str,
           click_event=RAction.run_command, color=RColor.white, style=None):
    ret = RText(message, color).set_hover_text(hover_text).set_click_event(click_event, click_content)
    if style is not None:
        return ret.set_styles(style)
    return ret


def on_user_info(server, info: Info):
    if info.content == command:
        info.cancel_send_to_server()
        on_player_joined(server, info.player, info)


def on_load(server: ServerInterface, prev_module):
    global logger
    generate_config(server)
    server.register_help_message(command, '显示欢迎消息')

    class DebugLogger(server.logger.__class__):
        DEFAULT_NAME = 'AdvJoinMOTD'

        def debug(self, *args):
            if verbose_mode:
                super(server.logger.__class__, self).debug(*args)

        def set_file(self, file_name):
            if self.file_handler is not None:
                self.removeHandler(self.file_handler)
            self.file_handler = logging.FileHandler(file_name, encoding='UTF-8')
            self.file_handler.setFormatter(self.FILE_FMT)
            self.addHandler(self.file_handler)
            return self

    logger = DebugLogger(server)


def write_readme(readme_path):
    ins = LineFormatter('', '')
    lineformatter_comment = ''
    for num in range(len(ins.comments)):
        lineformatter_comment += f'{num + 1}. {ins.comments[num]}\n'

    mcformatter_comment = ''
    count = 0
    for key, value in STYLE_ELEMENTS.items():
        count += 1
        mcformatter_comment += f'{key} {value} '
        if count % 8 == 0:
            mcformatter_comment += '\n'

    ver, channel = get_version_channel()

    with open(readme_path, 'w', encoding='UTF-8') as f:
        f.write(readme_text.format(
            plg_name,
            channel,
            ver,
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            lineformatter_comment,
            mcformatter_comment
            ))


def get_version_channel():
    parsed = parse('{ver}-{channel}', PLUGIN_METADATA['version'])
    if parsed is not None:
        ver, channel = parsed['ver'], parsed['channel'].capitalize()
    else:
        ver, channel = PLUGIN_METADATA['version'], 'Stable'
    return ver, channel


def generate_config(server: ServerInterface):
    global config_folder, reconfig_path
    config_folder = server.get_data_folder()
    reconfig_path = os.path.join(config_folder, 'regular.txt')
    readme_path = os.path.join(config_folder, 'ReadMe.txt')
    ver, channel = get_version_channel()
    current_readme_firstline = readme_text.splitlines()[0].format(plg_name, channel, ver)
    if not os.path.isdir(config_folder):
        os.mkdir(config_folder)

    if os.path.isfile(OLD_TEXT_FILE) and not os.path.isfile(reconfig_path):
        shutil.move(OLD_TEXT_FILE, reconfig_path)
    if not os.path.isfile(reconfig_path):
        with open(reconfig_path, 'w', encoding='UTF-8') as f:
            f.write(DEFAULT_TEXT)
    if not os.path.isfile(readme_path):
        write_readme(readme_path)
    else:
        with open(readme_path, 'r', encoding='UTF-8') as f:
            file_firstline = f.read().splitlines()[0]
        if file_firstline != current_readme_firstline:
            write_readme(readme_path)
