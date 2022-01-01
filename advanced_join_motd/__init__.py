import os
import json

from ruamel import yaml
from mcdreforged.api.types import CommandSource, InfoCommandSource, PluginServerInterface, Info
from mcdreforged.api.decorator import new_thread
from mcdreforged.api.command import *

from advanced_join_motd.config import config, JoinMOTD
from advanced_join_motd.utils import logger, tr_folder, gl_server, tr


class NoValidMOTD(Exception):
    pass


def on_player_joined(server: PluginServerInterface, player: str, info: Info):
    display(server, player)


@new_thread('AdvJoinMOTD_Main')
def display(server: PluginServerInterface, player: str):
    try:
        motd_list = config.get_current_join_motd()
        raw_text = None
        for item in motd_list:
            try:
                raw_text = item.text
            except:
                pass
        if raw_text is None:
            if not os.path.isfile(config.default_motd):
                raise NoValidMOTD
            motd = JoinMOTD.load(config.default_motd)
            raw_text = motd.text
        server.tell(player, raw_text)
        logger.debug(f'MOTD while {player} join is: \n{raw_text}')
    except Exception as e:
        server.tell(player, tr('exc.occurred', str(e)))
        logger.exception('Error occurred while running AdvancedJoinMOTD:')


def try_display(src: CommandSource):
    if isinstance(src, InfoCommandSource):
        display(src.get_server().as_plugin_server_interface(), str(src.get_info().player))
    else:
        raise RequirementNotMet('', '', 'Command can\'t be called by this command source')


def on_load(server: PluginServerInterface, prev_module):
    server.register_help_message(config.prefix, tr('help.mcdr'))
    server.register_command(
        Literal(config.prefix).runs(
            lambda src: try_display(src)
        ).requires(
            lambda src: isinstance(src, InfoCommandSource), lambda: 'Command can\'t be called by this command source'
        ).then(
            Literal('init').requires(
                lambda src: src.has_permission(config.administrator_permission)
            ).then(
                Literal('motd').runs(
                    lambda src: JoinMOTD.init_default()
                )
            ).then(
                Literal('schedule').runs(
                    lambda src: config.init_schedule()
                )
            )
        )
    )

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




