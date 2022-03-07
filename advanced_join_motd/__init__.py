import os
import json
import re

from typing import Iterable, Optional, Union, Tuple
from ruamel import yaml
from mcdreforged.api.types import CommandSource, InfoCommandSource, PluginServerInterface, Info, PlayerCommandSource
from mcdreforged.api.decorator import new_thread
from mcdreforged.api.command import *
from mcdreforged.api.rtext import *

from advanced_join_motd.config import config, JoinMOTDScheme, special_paras, Schedule
from advanced_join_motd.utils import logger, TRANSLATION_FOLDER, gl_server, tr, SCHEME_FOLDER, get_self_version


class NoValidScheme(Exception):
    def __init__(self, file_path: Optional[str] = None):
        file_path = '' if file_path is None else f': {file_path}'
        super().__init__(f"No available Scheme file found{file_path}")


def on_player_joined(server: PluginServerInterface, player: str, info: Info):
    display(server, player=player)


@new_thread('AdvJoinMOTD_Main')
def display(server: PluginServerInterface, player: str = None, file_name: Optional[str] = None):
    try:
        schedule_list = config.get_matched_schedules(player)
        # reverse = False, pop the scheme from the tail

        is_default = False

        def get_defined_scheme_data(scheme_name: str = None) -> Tuple[RTextBase, str]:
            nonlocal is_default
            if scheme_name is None:
                scheme_name = config.default_scheme_name
                is_default = True
            logger.debug(f'Trying to load scheme "{scheme_name}"')
            scheme_path = os.path.join(SCHEME_FOLDER, scheme_name)
            if not os.path.isfile(scheme_path):
                raise NoValidScheme(scheme_path)
            return JoinMOTDScheme.load(scheme_name).text, scheme_name

        def get_current_scheme_data(max_recursion: int = 10) -> Tuple[RTextBase, str]:
            schedule: Optional[Schedule] = schedule_list.pop() if len(schedule_list) != 0 else None
            try:
                return get_defined_scheme_data() if schedule is None else get_defined_scheme_data(schedule.file_name)
            except Exception as exc:
                if max_recursion >= 0 and not is_default:
                    return get_current_scheme_data(max_recursion - 1)
                else:
                    raise exc

        raw_text, file_name = get_current_scheme_data() if file_name is None else get_defined_scheme_data(file_name)

        logger.debug(f'Current scheme file: {file_name}')
        if player is None:
            logger.info('\n' + raw_text)
        else:
            server.tell(player, raw_text)
            logger.debug(f'JoinMOTD for {player} is: \n{raw_text}')
    except Exception as e:
        if player is not None:
            server.tell(player, tr('exc.occurred', e=str(e)))
        logger.exception('Error occurred while running AdvancedJoinMOTD:')


def show_help(src: CommandSource):
    src.reply(
        tr(
            'help.detailed',
            prefix=list(config.prefix)[0],
            plg_name=gl_server.get_self_metadata().name,
            ver=get_self_version()[0]
        ).set_translator(htr)
    )


def reload_self(src: CommandSource):
    exc, meta = None, gl_server.get_self_metadata()
    try:
        gl_server.reload_plugin(meta.id)
    except Exception as e:
        exc = e
        logger.exception("Error occurred while reloading {}".format(meta.name.replace(' ', '')))
    src.reply(tr('msg.reload_done'))
    if exc is not None:
        src.reply(RText(str(exc), color=RColor.red))


def info_scheme(src: CommandSource, file: str):
    to_reply, loaded_scheme = RTextList(), None
    if os.path.isfile(os.path.join(SCHEME_FOLDER, file)):
        def ftr(tr_key: str, *args, **kwargs):
            return tr(f'info.file.{tr_key}', *args, **kwargs)
        loaded_scheme = RTextList()
        loaded_scheme.append(
            ftr('title', file=file), '\n'
        )
        loaded_scheme.append(
            ftr('content'), ftr('click_here').h(tr('hover.preview', file=file)).c(
                RAction.run_command, f'{tuple(config.prefix)[0]} preview {file}'
            ).set_color(RColor.light_purple).set_styles((RStyle.underlined, RStyle.bold)), '\n'
        )
        to_reply.append(loaded_scheme)

    def sctr(tr_key: str, *args, **kwargs):
        return tr(f'info.sched.{tr_key}', *args, **kwargs)

    schedule_list = list()

    for s in sorted(config.all_schedules):
        if s.file_name == file:
            this_schedule = RTextList()
            for key, value in s.serialize().items():
                if key != 'file' and value is not None:
                    if len(this_schedule.children) != 0:
                        this_schedule.append('\n')
                    this_schedule.append(
                        sctr(key).set_color(RColor.aqua), f'§6{value}§r'
                    )
            schedule_list.append(this_schedule)

    if len(schedule_list) != 0:
        to_reply.append(
            sctr(
                'not_found', num=len(schedule_list)
            ).set_color(RColor.red) if loaded_scheme is None else sctr(
                'found', num=len(schedule_list)
            ).set_color(RColor.green),
            '\n'
        )
        num = 0
        for item in schedule_list:
            num += 1
            to_reply.append(f'[{num}] ', item)
    else:
        if loaded_scheme is None:
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


def register_command(server: PluginServerInterface):
    def __display(src: CommandSource, file_name: Optional[str] = None):
        args = [src]
        if isinstance(src, PlayerCommandSource):
            args.append(src.player)
        with RTextMCDRTranslation.language_context(src.get_preference().language):
            display(*args, file_name=file_name)

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
            Literal('scheme').runs(
                lambda src: JoinMOTDScheme.init_default()
            )
        ).then(
            Literal('schedule').runs(
                lambda src: config.init_schedule(src=src)
            )
        ),  # init
        Literal('reload').requires(
            lambda src: src.has_permission(config.administrator_permission)
        ).runs(
            lambda src: reload_self(src)
        ),  # reload
        Literal('preview').runs(
            lambda src: __display(src)
        ).then(
            QuotableText('file_name').runs(
                lambda src, ctx: __display(src, file_name=ctx['file_name'])
            )
        ),  # preview
        Literal('info').then(
            QuotableText('file_name').requires(
                lambda src: src.has_permission(config.administrator_permission)
            ).runs(
                lambda src, ctx: info_scheme(src, ctx['file_name'])
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

    register_command(server)

    if not os.path.isdir(SCHEME_FOLDER):
        os.makedirs(SCHEME_FOLDER)

    if not os.path.isfile(os.path.join(SCHEME_FOLDER, config.default_scheme_name)):
        JoinMOTDScheme.init_default(config.default_scheme_name)

    if os.path.isdir(TRANSLATION_FOLDER):
        for file in os.listdir(TRANSLATION_FOLDER):
            lang, data = None, {}
            with open(os.path.join(TRANSLATION_FOLDER, file), 'r', encoding='UTF-8') as f:
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
        os.makedirs(TRANSLATION_FOLDER)




