from typing import Union, List, Optional

from advanced_join_motd.utils.serializer import BlossomSerializable, ConfigurationBase


class PermissionRequirements(BlossomSerializable):
    reload: int = 3

    def get_permission(self, cmd: str, default_value: int):
        return self.serialize().get(cmd, default_value)


class Configuration(ConfigurationBase):
    command_prefix: Union[List[str], str] = ['!!ajm', '!!joinMOTD']
    permission_requirements: PermissionRequirements = PermissionRequirements.get_default()
    enable_permission_check: bool = True

    debug: bool
    verbosity: bool

    @property
    def prefix(self) -> List[str]:
        return list(set(self.command_prefix)) if isinstance(self.command_prefix, list) else [self.command_prefix]

    @property
    def primary_prefix(self) -> str:
        return self.prefix[0]

    @property
    def enable_debug_commands(self):
        return self.serialize().get('debug', False)

    @property
    def is_verbose(self):
        return self.serialize().get("verbosity", False)

    def after_load(self, plugin_inst):
        plugin_inst.set_verbose(self.is_verbose)

    def get_permission_checker(self, *cmd: str, default_value: int = 0):
        if not self.enable_permission_check:
            return lambda: True
        perm = default_value
        for item in cmd:
            current_item_perm = self.permission_requirements.get_permission(item, default_value)
            perm = perm if perm >= current_item_perm else current_item_perm
        return lambda src: src.has_permission(perm)
