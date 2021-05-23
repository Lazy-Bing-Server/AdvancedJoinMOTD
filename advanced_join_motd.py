# 1.x metadata
plg_name = 'Advanced Join MOTD'
plg_id = 'advanced_join_motd'
plg_desc = 'Custom your own join MOTD.'
PLUGIN_METADATA = {
    'id': plg_id,
    'version': '1',
    'name': plg_id,
    'description': plg_desc,
    'author': 'Ra1ny_Yuki',
    'link': 'https://github.com/Lazy-Bing-Server/AdvancedJoinMOTD',
    'dependencies':
    {
        'mcdreforged': '>= 0.8.1-alpha', # although it's useless xd
        'daycount': '*'
    }
}

command = '!!joinMOTD'
text_file = 'config/adv_joinmotd.txt'
default_text = r'''# 由{0} v{1}自动生成
# 转义字符: (转义内容均不可跨行)
# 1. # 仅适用于行首, 整行注释
# 2. %day% 开服时间
# 3. %serverlist: <servers>% 群组服子服列表, 引号后接子服务器列表<servers>, 使用空格分隔, 服务器列表不可换行
# 4. %7<text>% 一段含点击事件的浅灰色字符, 点击事件为执行指令, 指令内容即为<text>代表的字符串
# 5. %8<text>% 一段含点击事件的浅灰色字符, 点击事件为补全指令, 指令内容即为<text>代表的字符串
# 5. %a<text>% 一段含点击事件的黄绿色字符, 点击事件为复制到剪贴板, 复制内容即为<text>代表的字符串
# 6. %n<text>% 一段含点击事件的下划线字符, 点击事件为访问外部URL链接, URL即为<text>代表的字符串
# 7. %api: <url>% 从API获取文本并显示, 引号后接API地址
# 附录: Minecraft 字符样式转义字符串
# §4 绛红 §c 鲜红 §6 橙 §e 黄 §2 绿 §a 黄绿 §b 天蓝 §3 青 §1 深蓝 §9 亮蓝 §d 品红 §5 暗紫 §f 白 §7 浅灰 §8 深灰 §0 黑
# §r 取消一切样式和颜色 §l 加粗 §o 倾斜 §n 下划线 §m 删除线 §k 混淆
§7=======§r 欢迎回到 §eMy Server§7 =======§r
今天是 §e?§r 开服的第 §e%day%§r 天
§7-------§r Server List §7-------§r
%serverlist: survival mirror creative%
'''.strip().format(plg_name, PLUGIN_METADATA['version'])

# 0.x compatiable
try:
    from utils.rtext import *
except:
    from mcdreforged.api.rtext import *
from plugins.daycount import getday
from urllib.request import urlopen
import os
import re

def get_text() -> str:
    with open(text_file, 'r', encoding = 'UTF-8') as f:
        text = f.read()
    return text

def error_occured(server):
    error_text = 'JoinMOTD出错, 请通知管理员检查配置'
    server.say(RText(error_text, RColor.red))
    server.logger.warn(error_text)

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

def convert_text(text: str) -> RTextBase:
    return_text = ''
    for line in text.splitlines():
        if not line.startswith('#'):
            pattern = r'(?<=%)[\S ]*?(?=%)'
            rtext_ori = re.findall(pattern, line)
            normal_text_before = re.split(pattern, line)
            length = len(normal_text_before)
            normal_text = list()
            while length > 0:
                length -= 1
                normal_text.append(converted(list(normal_text_before[length]), length, len(normal_text_before)))
            normal_text.reverse()
            rtext_converted = list()
            for element in rtext_ori:
                element_content = element.lstrip('%').rstrip('%')
                if element_content == 'day':
                    rtext_converted.append(getday())
                elif element_content.startswith('serverlist:'):
                    server_list = element_content.split(':')[1].strip().split(' ')
                    server_text = ''
                    for server in server_list:
                        server_text += rclick(f'[§7{server}§r]', f'点击跳转到 §7{server}§r', f'/server {server}') + ' '
                    rtext_converted.append(server_text)
                elif element_content.startswith('7'):
                    rtext_converted.append(rclick(element_content.lstrip('7'), f'点击执行 §7{element_content.lstrip("7")}§r', element_content.lstrip('7'), color = RColor.gray))
                elif element_content.startswith('8'):
                    rtext_converted.append(rclick(element_content.lstrip('8'), f'点击执行 §7{element_content.lstrip("8")}§r', element_content.lstrip('8'), RAction.suggest_command, RColor.gray))
                elif element_content.startswith('a'):
                    rtext_converted.append(rclick(element_content.lstrip('a'), f'点击复制 §a{element_content.lstrip("a")}§r', element_content.lstrip('a'), RAction.open_url, RColor.green))
                elif element_content.startswith('n'):
                    rtext_converted.append(rclick(element_content.lstrip('n'), f'点击访问 §7{element_content.lstrip("n")}§r', element_content.lstrip('n'), RAction.open_url, style = RStyle.underlined))
                elif element_content.startswith('api:'):
                    rtext_converted.append(access_api(element_content.lstrip('api:')))
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
    
def access_api(url):
    try:
        return urlopen(url).read().decode('utf8').strip()
    except:
        return ''

def on_player_join(server, player, info):
    text = get_text()
    raw_text = convert_text(text)
    server.tell(player, raw_text)

def rclick(message: str, hover_text: str, click_content: str, click_event = RAction.run_command, color = RColor.white, style = None):
	ret = RText(message, color).set_hover_text(hover_text).set_click_event(click_event, click_content)
	if style != None:
		return ret.set_styles(style)
	return ret

def on_user_info(server, info):
    if info.content == command:
        on_player_join(server, info.player, info)
    
def on_load(server, prev_module):
    if not os.path.isdir(text_file):
        with open(text_file, 'w', encoding = 'UTF-8') as f:
            f.write(default_text)
    try:
        server.add_help_message(command, '显示欢迎消息')
    except:
        server.register_help_message(command, '显示欢迎消息')