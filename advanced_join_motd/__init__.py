import os
import json
import re

from typing import Iterable, Optional, Union
from ruamel import yaml
from mcdreforged.api.types import CommandSource, InfoCommandSource, PluginServerInterface, Info
from mcdreforged.api.decorator import new_thread
from mcdreforged.api.command import *
from mcdreforged.api.rtext import *

from advanced_join_motd.config import config, JoinMOTD, special_paras
from advanced_join_motd.utils import logger, tr_folder, gl_server, tr, motd_folder


class NoValidMOTD(Exception):
    pass


def on_player_joined(server: PluginServerInterface, player: str, info: Info):
    display(server, player)


@new_thread('AdvJoinMOTD_Main')
def display(server: PluginServerInterface, player: str, file_name: Optional[str] = None, is_console: bool = False):
    try:
        motd_list = config.get_current_join_motd(None if is_console else player)
        raw_text = None
        if file_name is None:
            for item in motd_list:
                try:
                    raw_text = item.motd.text
                except:
                    pass
                else:
                    file_name = item.file
            if raw_text is None:
                if not os.path.isfile(os.path.join(motd_folder, config.default_motd)):
                    raise NoValidMOTD('No available MOTD file found')
                motd = JoinMOTD.load(config.default_motd)
                raw_text, file_name = motd.text, config.default_motd
        else:
            if not os.path.isfile(os.path.join(motd_folder, file_name)):
                raise NoValidMOTD('No available MOTD file found')
            motd = JoinMOTD.load(file_name)
            raw_text, file_name = motd.text, config.default_motd
        server.tell(player, raw_text)
        logger.debug(f'Current MOTD file: {file_name}')
        logger.debug(f'MOTD while {player} join is: \n{raw_text}\n')
    except Exception as e:
        server.tell(player, tr('exc.occurred', e=str(e)))
        logger.exception('Error occurred while running AdvancedJoinMOTD:')


def show_help(src: CommandSource):
    meta = gl_server.get_self_metadata()
    src.reply(
        tr('help.detailed', prefix=list(config.prefix)[0], plg_name=meta.name, ver=meta.version).set_translator(htr)
    )


def try_display(src: CommandSource):
    if isinstance(src, InfoCommandSource):
        display(src.get_server().as_plugin_server_interface(), str(src.get_info().player))
    else:
        raise RequirementNotMet('', '', 'Command can\'t be called by this command source')


def reload_this(src: CommandSource):
    exc, meta = None, gl_server.get_self_metadata()
    try:
        gl_server.reload_plugin(meta.id)
    except Exception as e:
        exc = e
        logger.exception("Error occurred while reloading {}".format(meta.name.replace(' ', '')))
    src.reply(tr('msg.reload_done'))
    if exc is not None:
        src.reply(RText(str(exc), color=RColor.red))


def info(src: CommandSource, file: str):
    to_reply, loaded_motd = RTextList(), None
    if os.path.isfile(os.path.join(motd_folder, file)):
        def ftr(tr_key: str, *args, **kwargs):
            return tr(f'info.file.{tr_key}', *args, **kwargs)
        loaded_motd = RTextList()
        loaded_motd.append(
            ftr('title', file=file), '\n'
        )
        loaded_motd.append(
            ftr('content'), ftr('click_here').h(tr('hover.preview', file=file)).c(
                RAction.run_command, f'{tuple(config.prefix)[0]} preview {file}'
            ).set_color(RColor.light_purple).set_styles((RStyle.underlined, RStyle.bold)), '\n'
        )
        to_reply.append(loaded_motd)

    def sctr(tr_key: str, *args, **kwargs):
        return tr(f'info.sched.{tr_key}', *args, **kwargs)

    sched_list = list()

    for s in sorted(config.schedule):
        if s.file == file:
            this_sched = RTextList()
            for key, value in s.serialize().items():
                if key != 'file' and value is not None:
                    if len(this_sched.children) != 0:
                        this_sched.append('\n')
                    this_sched.append(
                        sctr(key).set_color(RColor.aqua), f'§6{value}§r'
                    )
            sched_list.append(this_sched)

    if len(sched_list) != 0:
        to_reply.append(
            sctr(
                'not_found', num=len(sched_list)
            ).set_color(RColor.red) if loaded_motd is None else sctr(
                'found', num=len(sched_list)
            ).set_color(RColor.green),
            '\n'
        )
        num = 0
        for item in sched_list:
            num += 1
            to_reply.append(f'[{num}] ', item)
    else:
        if loaded_motd is None:
            to_reply = sctr('both_not_found')

    src.reply(to_reply)


def htr(key: str, *args, **kwargs) -> Union[str, RTextBase]:
    help_message, help_msg_rtext = gl_server.tr(key, *args, **kwargs), RTextList()
    if not isinstance(help_message, str):
        logger.error('Error translate text "{}"'.format(key))
        return key
    for line in help_message.splitlines():
        result = re.search(r'(?<=§7){}[\S ]*?(?=§)'.format(list(config.prefix)[0]), line)
        if result is not None:
            cmd = result.group().strip() + ' '
            help_msg_rtext.append(RText(line).c(RAction.suggest_command, cmd).h(tr('hover.suggest', cmd=cmd)))
        else:
            help_msg_rtext.append(line)
        if line != help_message.splitlines()[-1]:
            help_msg_rtext.append('\n')
    return help_msg_rtext


def init_help(src: CommandSource):
    src.reply(tr('help.init', prefix=list(config.prefix)[0]).set_translator(htr))


def register_command():
    root = Literal(config.prefix).runs(
            lambda src: show_help(src)
        ).requires(
            lambda src: isinstance(src, InfoCommandSource), lambda: 'Command can\'t be called by this command source'
        )
    arg_nodes = [
        Literal('init').requires(
            lambda src: src.has_permission(config.administrator_permission)
        ).runs(
            lambda src: init_help(src)
        ).then(
            Literal('motd').runs(
                lambda src: JoinMOTD.init_default()
            )
        ).then(
            Literal('schedule').runs(
                lambda src: config.init_schedule(src=src)
            )
        ),  # init
        Literal('reload').requires(
            lambda src: src.has_permission(config.administrator_permission)
        ).runs(
            lambda src: reload_this(src)
        ),  # reload
        Literal('preview').runs(
            lambda src: display(src.get_server().as_plugin_server_interface(), str(src.get_info().player))
        ).then(
            QuotableText('file_name').runs(
                lambda src, ctx: display(src.get_server().as_plugin_server_interface(), str(src.get_info().player), ctx['file_name'])
            )
        ),  # preview
        Literal('info').then(
            QuotableText('file_name').requires(
                lambda src: src.has_permission(config.administrator_permission)
            ).runs(
                lambda src, ctx: info(src, ctx['file_name'])
            )
        )
    ]
    full_tree = root
    for item in arg_nodes:
        root.then(item)
    gl_server.register_command(full_tree)


def on_load(server: PluginServerInterface, prev_module):
    if isinstance(config.prefix, Iterable):
        for p in config.prefix:
            server.register_help_message(p, tr('help.mcdr'))
    elif isinstance(config.prefix, str):
        server.register_help_message(config.prefix, tr('help.mcdr'))
    else:
        raise TypeError('Prefix type is not str or list')

    register_command()

    if not os.path.isdir(motd_folder):
        os.makedirs(motd_folder)

    if not os.path.isfile(os.path.join(motd_folder, config.default_motd)):
        JoinMOTD.init_default(config.default_motd)

    if os.path.isdir(tr_folder):
        for file in os.listdir(tr_folder):
            lang, data = None, {}
            with open(os.path.join(tr_folder, file), 'r', encoding='UTF-8') as f:
                if file.endswith('.json'):
                    data = json.load(f)
                    lang = file[:-5] if isinstance(data, dict) else None
                if file.endswith('.yaml') or file.endswith('.yml'):
                    try:
                        data = dict(**yaml.round_trip_load(f))
                        lang = file[:-5] if file.endswith('yaml') else file[:-4]
                    except:
                        lang = None
            if lang is not None:
                data = {f'{gl_server.get_self_metadata().id}.{key}': value for key, value in data.copy().items()}
                server.register_translation(lang, data)
    else:
        os.makedirs(tr_folder)




