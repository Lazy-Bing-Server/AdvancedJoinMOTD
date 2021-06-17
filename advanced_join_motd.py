# 1.x metadata
plg_name = 'Advanced Join MOTD'
plg_id = 'advanced_join_motd'
plg_desc = 'Custom your own join MOTD.'
PLUGIN_METADATA = {
    'id': plg_id,
    'version': '4',
    'name': plg_id,
    'description': plg_desc,
    'author': 'Ra1ny_Yuki',
    'link': 'https://github.com/Lazy-Bing-Server/AdvancedJoinMOTD',
    'dependencies':
    {
        'mcdreforged': '>= 1.5.0' # although it's useless xd
    }
}

from mcdreforged.api.all import *
from parse import parse
from urllib.request import urlopen
try:
    from plugins.daycount import getday
    daycount_imported = True
except:
    daycount_imported = False
import os
import re
import time
import shutil
import datetime
import collections

command = '!!joinMOTD'
readme_text = '''
本说明由{0} (插件版本: Snapshot Build {1})自动生成, 修订时间: 2021-06-17 18:30:00
生成时间: {2}

一. 时间特定的欢迎文本：
默认显示regular.txt内包含的文本
低于build 3版本的配置文本会被自动移动到regular.txt, 不会覆盖已存在的regular.txt
当需要在特定时间段显示特定欢迎文本时, 请新建文本文件
文件名格式可为如下两种:
其中的任意元素可以替换为~表示未指定, 当该元素为未指定时不同格式会有不同处理原则
1.<秒>_<分>_<时>_<日>_<月>_<年>_<星期几>.txt
    将当前时间与该文件名所表示的时间表达式进行匹配
    当且仅当全部元素匹配成功时显示该文本文件中的文字
    当元素未指定时默认为匹配成功
2.<秒>_<分>_<时>_<日>_<月>_<年>;<秒>_<分>_<时>_<日>_<月>_<年>.txt
    将当前时间与该文件名所表示的两个时间点进行比较
    当且仅当目前时间处于两者之间的闭区间中时(无所谓时间)显示该文本文件中的文字
    当秒分时未指定时会被置为0
    当日月年未制定时会被置为当前时间的日月年

二. 转义字符: (转义内容均不可跨行)
可以利用转义字符为其添加各种元素
1. # 仅适用于行首, 整行注释
2. %day% 开服时间
3. %serverlist: <servers>% 群组服子服列表, 引号后接子服务器列表<servers>, 使用空格分隔, 服务器列表不可换行
4. %7<text>% 一段含点击事件的浅灰色字符, 点击事件为执行指令, 指令内容即为<text>代表的字符串
5. %8<text>% 一段含点击事件的浅灰色字符, 点击事件为补全指令, 指令内容即为<text>代表的字符串
6. %a<text>% 一段含点击事件的黄绿色字符, 点击事件为复制到剪贴板, 复制内容即为<text>代表的字符串
7. %n<text>% 一段含点击事件的下划线字符, 点击事件为访问外部URL链接, URL即为<text>代表的字符串
8. %API: <url>% 从API获取文本并显示, 引号后接API地址
9. %since: <date>% 自某日开始至今的日期的绝对值, 输入日期应形如yyyy-mm-dd
10. %player% 上线玩家名称
11. %playerlist% 当前全部玩家列表
附录: Minecraft 字符样式转义代码
§4 绛红 §c 鲜红 §6 橙 §e 黄 §2 绿 §a 黄绿 §b 天蓝 §3 青 §1 深蓝 §9 亮蓝 §d 品红 §5 暗紫 §f 白 §7 浅灰 §8 深灰 §0 黑
§r 取消一切样式和颜色 §l 加粗 §o 倾斜 §n 下划线 §m 删除线 §k 混淆'''.strip()

default_text = r'''
§7=======§r 欢迎回到 §eMy Server§7 =======§r
今天是 §e?§r 开服的第 §e%day%§r 天
§7-------§r Server List §7-------§r
%serverlist: survival mirror creative%
'''

old_text_file = 'config/adv_joinmotd.txt' # Old text file to auto migrate, do not change!
style_elements = ['§4', '§c', '§6', '§e', '§2', '§a', '§b', '§3', '§1', '§9', '§d', '§5', '§f', '§7', '§8', '§0', '§r', '§l', '§o', '§n', '§m', '§k']
click_events = {'7': RAction.run_command, '8': RAction.suggest_command, 'a': RAction.copy_to_clipboard, 'n': RAction.open_url}
hover_element = {'7': '执行', '8': '补全', 'a': '复制', 'n': '访问'}
time_format = collections.namedtuple('time_format', 'sec min hrs date mon yrs day')


def get_text() -> str:
    text_file = os.path.join(config_folder, choose_file())
    with open(text_file, 'r', encoding = 'UTF-8') as f:
        text = f.read()
    return text

def now_time(unix = False):
    if unix:
        return int(time.mktime(datetime.datetime.now().timetuple()))
    return datetime.datetime.now()

def nowdict():
    now_list_raw = now_time().strftime('%S %M %H %d %m %Y %w').split(' ')
    now_list = []
    for element in now_list_raw:
        now_list.append(int(element))
    now_list[-1] += 1
    if now_list[-1] == 7:
        now_list[-1] = 0
    return time_format._make(now_list)._asdict()

def is_matched(dt: dict):
    now_dict = nowdict()
    for key, value in dt.items():
        if value == '~':
            value_after = None
        else:
            value_after = int(value)
        if not bool(value_after == now_dict[key] or value_after is None):
            return False
    return True

def to_unix_timestamp(t: time_format):
    print(time.mktime(time.strptime(f'{t.sec} {t.min} {t.hrs} {t.date} {t.mon} {t.yrs}', '%S %M %H %d %m %Y')))
    return time.mktime(time.strptime(f'{t.sec} {t.min} {t.hrs} {t.date} {t.mon} {t.yrs}', '%S %M %H %d %m %Y'))

def is_in_range(from_time: int, to_time: int):
    now_timestamp = now_time(True)
    print(now_timestamp)
    time_list = [from_time, to_time, now_timestamp]
    if max(time_list) != now_timestamp and min(time_list) != now_timestamp:
        return True
    elif now_timestamp == from_time or now_timestamp == to_time:
        return True
    else:
        return False

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
    from_time = time_format._make(formatted_from_to[:6] + [None])
    to_time = time_format._make(formatted_from_to[6:] + [None])
    return to_unix_timestamp(from_time), to_unix_timestamp(to_time)

def is_current(file_name: str):
    ret = 'regular.txt'
    format_from_to = parse('{from_sec}_{from_min}_{from_hrs}_{from_date}_{from_mon}_{from_yrs};{to_sec}_{to_min}_{to_hrs}_{to_date}_{to_mon}_{to_yrs}.txt', file_name)
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

def converted(text, num, max):
    try:
        if text[0] == '%' and num != 0:
            text.pop(0)
        if text[-1] == '%' and num != max - 1:
            text.pop(-1)
    except: pass
    text_after = ''
    for item in text:
        text_after += item
    return text_after

def convert_text(server: ServerInterface, text: str, player: str) -> RTextBase:
    return_text = ''
    for line in text.splitlines():
        if not line.startswith('#'):
            pattern = r'%[\S ]*?%'
            rtext_ori = re.findall(pattern, line)
            normal_text = re.split(pattern, line)            
            rtext_converted = list()
            for element in rtext_ori:
                element_content = element[1:-1].strip()
                if element_content == 'day' and daycount_imported:
                    rtext_converted.append(getday())
                elif element_content == 'player':
                    rtext_converted.append(player)
                elif element_content == 'playerlist':
                    player_list = str(server.rcon_query('list')).split(' players online:')[1].strip().split(',')
                    playerlist = ''
                    for player_name in player_list:
                        if playerlist != '': playerlist += ', '
                        playerlist += player_name.strip()
                    rtext_converted.append(playerlist)
                elif element_content.startswith('serverlist:'): 
                    server_list = element_content[11:].strip().split(',')
                    server_text = ''
                    for server_ in server_list:
                        l = parse('[{outer}]({inner})', server_.strip())
                        if l: outer, inner = l['outer'], l['inner']
                        else: outer, inner = server_.strip(), server_.strip()
                        server_text += rclick(f'[§7{outer}§r]', f'点击跳转到 §7{inner}§r', f'/server {inner}') + ' '
                    rtext_converted.append(server_text)
                elif list(element_content)[0] in click_events.keys():
                    l = parse('{event}[{name}]({content})', element_content)
                    if l: pre, event, hover, name, content = l['event'], click_events[l['event']], hover_element[l['event']], l['name'], l['content']
                    else: pre, event, hover, name, content = list(element_content)[0], click_events[list(element_content)[0]], hover_element[list(element_content)[0]], element_content[1:], clean(element_content[1:])
                    if pre == '8': pre, content = '7', content.strip() + ' '
                    rtext_converted.append(rclick(f"§{pre}{name}§r", f"点击{hover} §7{content}§r", content, event))
                elif element_content.startswith('API:'):
                    rtext_converted.append(access_api(element_content[4:].strip()))
                elif element_content.startswith('since:'):
                    rtext_converted.append(get_day(element_content[6:].strip()))
                else:
                    rtext_converted.append(element)
            num = 0
            final_line = ''
            while num <= len(normal_text):
                final_line += str(normal_text[num])
                num += 1
                if num == len(normal_text):
                    break
                final_line += rtext_converted[num - 1]
            if return_text != '':
                return_text += '\n'
            return_text += final_line
    return return_text

def get_day(startday: str):
    output = datetime.datetime.now() - datetime.datetime.strptime(startday, '%Y-%m-%d')
    return str(abs(output.days))
    
def clean(msg: str):
    for item in style_elements:
        msg = msg.replace(item, '')
    return msg

def access_api(url: str):
    try:
        return urlopen(url).read().decode('utf8').strip()
    except:
        return ''

def on_player_joined(server: ServerInterface, player: str, info: Info):
    try:
        text = get_text()
        raw_text = convert_text(server, text, player)
        server.tell(player, raw_text)
    except Exception as e:
        server.tell(player, f'Advanced Join MOTD出现错误, 请通知管理员处理, 错误如下: \n§c{e}§r')
        raise

def rclick(message: str, hover_text: str, click_content: str, click_event = RAction.run_command, color = RColor.white, style = None):
	ret = RText(message, color).set_hover_text(hover_text).set_click_event(click_event, click_content)
	if style != None:
		return ret.set_styles(style)
	return ret

def on_user_info(server, info):
    if info.content == command:
        on_player_joined(server, info.player, info)
    
def on_load(server: ServerInterface, prev_module):
    global logger
    generate_config(server)
    server.register_help_message(command, '显示欢迎消息')
    logger = server.logger

def generate_config(server: ServerInterface):
    def write_readme(readme_path):
        with open(readme_path, 'w', encoding='UTF-8') as f:
            f.write(readme_text.format(plg_name, PLUGIN_METADATA['version'], datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    global config_folder, reconfig_path
    config_folder = server.get_data_folder()
    reconfig_path = os.path.join(config_folder, 'regular.txt')
    readme_path = os.path.join(config_folder, 'ReadMe.txt')
    current_readme_firstline = readme_text.splitlines()[0].format(plg_name, PLUGIN_METADATA['version'])
    if not os.path.isdir(config_folder):
        os.mkdir(config_folder)
    if os.path.isfile(old_text_file) and not os.path.isfile(reconfig_path):
        shutil.move(old_text_file, reconfig_path)
    if not os.path.isfile(reconfig_path):
        with open(reconfig_path, 'w', encoding='UTF-8') as f:
            f.write(default_text)
    if not os.path.isfile(readme_path):
        write_readme(readme_path)
    else:
        with open(readme_path, 'r', encoding='UTF-8') as f:
            file_firstline = f.read().splitlines()[0]
        if file_firstline != current_readme_firstline:
            write_readme(readme_path)
