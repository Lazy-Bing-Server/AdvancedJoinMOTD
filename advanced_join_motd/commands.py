from typing import Union, Iterable, List, TYPE_CHECKING, Optional
from mcdreforged.api.types import CommandSource, PlayerCommandSource, InfoCommandSource
from mcdreforged.api.command import *
from mcdreforged.api.rtext import *

from advanced_join_motd.utils.translation import htr, rtr


if TYPE_CHECKING:
    from advanced_join_motd.advanced_join_motd import AdvancedJoinMOTD
    from advanced_join_motd.api import AbstractJoinMOTDScheme


class CommandManager:
    def __init__(self, plugin_inst: "AdvancedJoinMOTD"):
        self.plugin_inst = plugin_inst

    @property
    def server(self):
        return self.plugin_inst.server

    @property
    def config(self):
        return self.plugin_inst.config

    def show_help(self, source: CommandSource):
        meta = self.server.get_self_metadata()
        source.reply(
            htr(
                'help.detailed',
                _lb_htr_prefixes=self.config.prefix,
                prefix=self.config.primary_prefix,
                name=meta.name,
                ver=str(meta.version)
            )
        )

    def reload_self(self, source: CommandSource):
        self.config.set_reloader(source)
        self.server.reload_plugin(self.server.get_self_metadata().id)
        source.reply(rtr('loading.reloaded'))

    def preview(self, source: InfoCommandSource, scheme_name: Optional[str] = None):
        info = source.get_info()
        player = source.player if isinstance(source, PlayerCommandSource) else None
        if scheme_name is None:
            self.plugin_inst.scheme_manager.on_player_joined(self.plugin_inst.server, player, info)
        else:
            try:
                text = "\n" + self.plugin_inst.scheme_manager.schemes[scheme_name].get_scheme_text(player, info)
            except Exception as exc:
                text = rtr('preview.generated_failed', scheme_name=scheme_name)
                self.plugin_inst.logger.exception(text)
                text += str(exc)
                text.set_color(RColor.red)
            source.reply(text)

    def list_loaded(self, source: CommandSource):
        schemes = self.plugin_inst.scheme_manager.schemes
        text = [rtr('list.title', len(schemes))]
        for num, scheme in enumerate(sorted(schemes.values())):  # type: int, AbstractJoinMOTDScheme
            num += 1
            name = scheme.get_name()
            text.append(
                RText.format(f'[{num}] §b§l{name}§r').c(
                    RAction.run_command, f'{self.config.primary_prefix} info {name}'
                ).h(
                    rtr('list.hover', name)
                )
            )
        source.reply(RText.join('\n', text))

    def info_scheme(self, source: CommandSource, scheme_name: str):
        scheme = self.plugin_inst.scheme_manager.schemes.get(scheme_name)
        click_to_preview = rtr('info.click_to_preview.text').c(
            RAction.run_command, f'{self.config.primary_prefix} preview {scheme_name}'
        ).h(
            rtr('info.click_to_preview.hover', scheme_name)
        )
        player = source.player if isinstance(source, PlayerCommandSource) else "console"
        avail = scheme.is_enabled(player)
        source.reply(
            rtr(
                'info.text',
                scheme_name=scheme_name,
                plugin_id=scheme.server.get_self_metadata().id,
                plugin_ver=scheme.server.get_self_metadata().version,
                priority=scheme.get_priority(),
                avail=str('a' if avail else 'c') + str(avail),
                click_to_preview=click_to_preview
            )
        )

    def register_command(self):
        def permed_literal(literals: Union[str, Iterable[str]]) -> Literal:
            literals = {literals} if isinstance(literals, str) else set(literals)
            return Literal(literals).requires(self.config.get_permission_checker(*literals))

        root_node: Literal = Literal(self.config.prefix).runs(lambda src: self.preview(src)).requires(lambda src: isinstance(src, InfoCommandSource))

        children: List[AbstractNode] = [
            Literal('help').runs(lambda src: self.show_help(src)),
            permed_literal('reload').runs(lambda src: self.reload_self(src)),
            permed_literal('list').runs(lambda src: self.list_loaded(src)),
            permed_literal('info').then(
                GreedyText('name').runs(lambda src, ctx: self.info_scheme(src, ctx['name'])).requires(
                    lambda src, ctx: self.plugin_inst.scheme_manager.schemes.get(ctx['name']) is not None,
                    lambda src, ctx: rtr('preview.not_found', ctx['name'])
                ).suggests(lambda: self.plugin_inst.scheme_manager.schemes.keys())
            ),
            permed_literal('preview').runs(
                lambda src: self.preview(src)
            ).then(
                GreedyText('name').runs(lambda src, ctx: self.preview(src, ctx['name'])).requires(
                    lambda src, ctx: self.plugin_inst.scheme_manager.schemes.get(ctx['name']) is not None,
                    lambda src, ctx: rtr('preview.not_found', ctx['name'])
                ).suggests(lambda: self.plugin_inst.scheme_manager.schemes.keys())
            )
        ]

        debug_nodes: List[AbstractNode] = []

        if self.config.enable_debug_commands:
            children += debug_nodes

        for node in children:
            root_node.then(node)

        self.server.register_command(root_node)
