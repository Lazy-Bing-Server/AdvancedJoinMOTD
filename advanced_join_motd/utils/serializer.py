import os
import shutil
from typing import List, Optional, Tuple, get_origin, Type, TYPE_CHECKING

from mcdreforged.api.types import CommandSource
from mcdreforged.api.utils import Serializable, deserialize
from ruamel import yaml

from advanced_join_motd.utils import file_util
from advanced_join_motd.utils.misc import psi
from advanced_join_motd.utils.translation import ktr, TRANSLATION_KEY_PREFIX

if TYPE_CHECKING:
    from advanced_join_motd.advanced_join_motd import AdvancedJoinMOTD


class BlossomSerializable(Serializable):
    @classmethod
    def _fix_data(cls, data: dict, *, father_nodes: Optional[List[str]] = None) -> Tuple[dict, List[str]]:
        needs_save = list()
        annotations = cls.get_field_annotations()
        default_data = cls.get_default().serialize()
        if father_nodes is None:
            father_nodes = []
        fixed_dict = {}

        for key, target_type in annotations.items():
            current_nodes = father_nodes.copy()
            current_nodes.append(key)
            node_name = '.'.join(current_nodes)
            if key not in data.keys():
                if key in default_data.keys():
                    needs_save.append(node_name)
                    fixed_dict[key] = default_data[key]
                continue
            value = data[key]

            def fix_blossom(single_type: Type[BlossomSerializable], single_data: dict):
                nonlocal needs_save
                single_data, save_nodes = single_type._fix_data(single_data, father_nodes=current_nodes)
                needs_save += save_nodes
                return single_data

            if get_origin(target_type) is None and issubclass(target_type, BlossomSerializable):
                value = fix_blossom(target_type, value)
            else:
                try:
                    value = deserialize(value, target_type, error_at_redundancy=True)
                except (ValueError, TypeError):
                    needs_save.append(node_name)
                    if key not in default_data.keys():
                        continue
                    if isinstance(target_type, Serializable):
                        value = target_type.get_default().serialize()
                    else:
                        try:
                            value = target_type(value)
                        except:
                            value = default_data[key]
            fixed_dict[key] = value
        return fixed_dict, needs_save


class ConfigurationBase(BlossomSerializable):
    __rt_yaml = yaml.YAML(typ='rt')
    __safe_yaml = yaml.YAML(typ='safe')
    for item in (__rt_yaml, __safe_yaml):  # type: yaml.YAML
        item.width = 1048576
        item.indent(2, 2, 2)

    def __init__(self, **kwargs):
        self.__file_path = None
        self.__bundled_template_path = None
        self.__reloader: Optional[CommandSource] = None
        self.__plugin_inst = None
        super().__init__(**kwargs)

    def set_reloader(self, source: Optional[CommandSource] = None):
        self.__reloader = source

    @property
    def logger(self):
        if self.__plugin_inst is not None:
            return self.__plugin_inst.logger
        return None

    @property
    def reloader(self):
        return self.__reloader

    def get_template(self) -> yaml.CommentedMap:
        try:
            with psi.open_bundled_file(self.__bundled_template_path) as f:
                return self.__rt_yaml.load(f)
        except Exception as e:
            self.logger.warning("Template not found, is plugin modified?", exc_info=e)
            return yaml.CommentedMap()

    def after_load(self, plugin_inst: "AdvancedJoinMOTD"):
        pass

    def set_config_attr(self, file_path: str, plugin_inst: "AdvancedJoinMOTD", bundled_template_path: Optional[str] = None):
        self.__file_path = file_path
        self.__bundled_template_path = bundled_template_path
        self.__plugin_inst = plugin_inst

    @classmethod
    def load(
            cls,
            plugin_inst: "AdvancedJoinMOTD",
            file_path: str = 'config.yml',
            bundled_template_path: str = os.path.join("resources", "default_cfg.yml"),
            in_data_folder: bool = True,
            print_to_console: bool = True,
            source_to_reply: Optional[CommandSource] = None,
            encoding: str = 'utf8'
    ):
        def log(translation_key, *args, _lb_rtr_prefix=TRANSLATION_KEY_PREFIX + 'config.', **kwargs):
            text = ktr(translation_key, *args, _lb_rtr_prefix=_lb_rtr_prefix, **kwargs, )
            if print_to_console:
                plugin_inst.logger.info(text)
            if source_to_reply is not None:
                source_to_reply.reply(text)


        default_config = cls.get_default().serialize()
        needs_save = False
        if in_data_folder:
            file_path = os.path.join(plugin_inst.get_data_folder(), file_path)

        # Load & Fix data
        try:
            string = file_util.lf_read(file_path, encoding=encoding)
            read_data: dict = cls.__safe_yaml.load(string)
        except:
            # Reading failed, remove current file
            file_util.delete(file_path)
            result_config = default_config.copy()
            needs_save = True
            log("Fail to read config file, using default config")
        else:
            # Reading file succeeded, fix data
            result_config, nodes_require_save = cls._fix_data(read_data)
            if len(nodes_require_save) > 0:
                needs_save = True
                log("Fixed invalid config keys with default values, please confirm these values: ")
                log(', '.join(nodes_require_save))
        try:
            # Deserialize into configuration instance, should have raise no exception in theory
            result_config = cls.deserialize(result_config)
        except:
            # But if exception is raised, that indicates config definition error
            result_config = cls.get_default()
            needs_save = True
            log("Fail to read config file, using default config")

        result_config.set_config_attr(file_path, plugin_inst, bundled_template_path=bundled_template_path)
        if needs_save:
            # Saving config
            result_config.save(encoding=encoding, print_to_console=print_to_console, source_to_reply=source_to_reply)

        result_config.after_load(plugin_inst)
        log('server_interface.load_config_simple', _lb_rtr_prefix='', _lb_tr_default_fallback='Config loaded')
        return result_config

    def save(
            self,
            encoding: str = 'utf8',
            print_to_console: bool = True,
            source_to_reply: Optional[CommandSource] = None
    ):
        def log(translation_key, *args, _lb_rtr_prefix=TRANSLATION_KEY_PREFIX + 'config.', **kwargs):
            text = ktr(translation_key, *args, _lb_rtr_prefix=_lb_rtr_prefix, **kwargs)
            if print_to_console:
                self.logger.info(text)
            if source_to_reply is not None:
                source_to_reply.reply(text)

        file_path = self.__file_path
        config_temp_path = os.path.join(os.path.dirname(file_path), f"temp_{os.path.basename(file_path)}")

        if os.path.isdir(file_path):
            shutil.rmtree(file_path)

        def _save(safe_dump: bool = False):
            if os.path.exists(config_temp_path):
                file_util.delete(config_temp_path)

            config_content = self.serialize()
            if safe_dump:
                with file_util.safe_write(file_path, encoding=encoding) as f:
                    self.__safe_yaml.dump(config_content, f)
                self.logger.warning("Validation during config file saving failed, saved without original format")
            else:
                formatted_config: yaml.CommentedMap
                if os.path.isfile(file_path):
                    formatted_config = self.__rt_yaml.load(file_util.lf_read(file_path, encoding=encoding))
                else:
                    formatted_config = self.get_template()
                for key, value in config_content.items():
                    formatted_config[key] = value
                with file_util.safe_write(config_temp_path, encoding=encoding) as f:
                    self.__rt_yaml.dump(formatted_config, f)
                try:
                    self.deserialize(self.__safe_yaml.load(file_util.lf_read(config_temp_path, encoding=encoding)))
                except (TypeError, ValueError):
                    log("Attempting saving config with original file format due to validation failure while attempting saving config and keep local config file format")
                    log("There may be mistakes in original config file format, please contact plugin maintainer")
                    _save(safe_dump=True)
                else:
                    os.replace(config_temp_path, file_path)
        _save()
