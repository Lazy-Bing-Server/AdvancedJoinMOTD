# 1.x metadata
plg_name = 'Advanced Join MOTD'
plg_id = 'advanced_join_motd'
plg_desc = 'Custom your own join MOTD.'
PLUGIN_METADATA = {
    'id': plg_id,
    'version': '3',
    'name': plg_id,
    'description': plg_desc,
    'author': 'Ra1ny_Yuki',
    'link': 'https://github.com/Lazy-Bing-Server/AdvancedJoinMOTD',
    'dependencies':
    {
        'mcdreforged': '>=0.8.1-alpha', # although it's useless xd
        'daycount': '*'
    }
}

command = '!!joinMOTD'
text_file = 'config/adv_joinmotd.txt'
default_text = r'''# 由{0} build{1}自动生成
# 转义字符: (转义内容均不可跨行)
# 1. # 仅适用于行首, 整行注释
# 2. %day% 开服时间
# 3. %serverlist: <servers>% 群组服子服列表, 引号后接子服务器列表<servers>, 使用逗号分隔, 服务器列表不可换行
# 4. %7<text>% 一段含点击事件的浅灰色字符, 点击事件为执行指令, 指令内容即为<text>代表的字符串
# 5. %8<text>% 一段含点击事件的浅灰色字符, 点击事件为补全指令, 指令内容即为<text>代表的字符串
# 5. %a<text>% 一段含点击事件的黄绿色字符, 点击事件为复制到剪贴板, 复制内容即为<text>代表的字符串
# 6. %n<text>% 一段含点击事件的下划线字符, 点击事件为访问外部URL链接, URL即为<text>代表的字符串
# 注意: 自build 3开始, 34567中的<server>和<text>格式可以填写为[<outer>](<inner>)
# 即显示的内容为<outer>点击事件的内容为<inner>, <outer>内容依然会被施加默认样式
# 提示: 如需取消点击事件的默认样式仅需在<text>最前加上取消样式的§r即可, 还可另附样式, 添加的字符样式转义不会影响点击事件内容(指令, 复制文本和URL)
# 上述仅适用于点击事件与显示文本一致的情况, 若不一致则需在<outer>前附加
# 7. %API: <url>% 从API获取文本并显示, 引号后接API地址
# 8. %since: <date>% 自某日开始至今的日期的绝对值, 输入日期应形如yyyy-mm-dd
# 9. %player%: 加入的玩家名称
# 10. %playerlist% 当前全部在线玩家名称
# 附录: Minecraft 字符样式转义字符串
# §4 绛红 §c 鲜红 §6 橙 §e 黄 §2 绿 §a 黄绿 §b 天蓝 §3 青 §1 深蓝 §9 亮蓝 §d 品红 §5 暗紫 §f 白 §7 浅灰 §8 深灰 §0 黑
# §r 取消一切样式和颜色 §l 加粗 §o 倾斜 §n 下划线 §m 删除线 §k 混淆
# ======= 请在本行以下填写欢迎文本内容 =======
§7=======§r 欢迎回到 §eMy Server§7 =======§r
今天是 §e?§r 开服的第 §e%day%§r 天
§7-------§r Server List §7-------§r
%serverlist: survival mirror creative%
'''.strip().format(plg_name, PLUGIN_METADATA['version'])


try:
    from utils.rtext import * # MCDReforged 0.8.1-0.9.8 compatiable
except:
    from mcdreforged.api.rtext import * # MCDReforged 1.0+ comaptiable
from urllib.request import urlopen

from parse import parse
try:
    from plugins.daycount import getday
    daycount_imported = True
except:
    daycount_imported = False
import os
import re
import datetime
style_elements = ['§4', '§c', '§6', '§e', '§2', '§a', '§b', '§3', '§1', '§9', '§d', '§5', '§f', '§7', '§8', '§0', '§r', '§l', '§o', '§n', '§m', '§k']
click_events = {'7': RAction.run_command, '8': RAction.suggest_command, 'a': RAction.copy_to_clipboard, 'n': RAction.open_url}
hover_element = {'7': '执行', '8': '补全', 'a': '复制', 'n': '访问'}

def get_text() -> str:
    with open(text_file, 'r', encoding = 'UTF-8') as f:
        text = f.read()
    return text

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

def convert_text(server, text: str, player: str) -> RTextBase:
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

def access_api(url):
    try:
        return urlopen(url).read().decode('utf8').strip()
    except:
        return ''

def on_player_joined(server, player, info):
    try:
        if not os.path.isfile:
            with open(text_file, 'w', encoding = 'UTF-8') as f:
                f.write(default_text)
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
    
def on_load(server, prev_module):
    if not os.path.isfile(text_file):
        with open(text_file, 'w', encoding = 'UTF-8') as f:
            f.write(default_text)
    try:
        server.add_help_message(command, '显示欢迎消息')
    except:
        server.register_help_message(command, '显示欢迎消息')
