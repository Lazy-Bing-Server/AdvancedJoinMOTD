from advanced_join_motd.cli_entry import init_schedule, init_extra_config, init_default_motd
import sys
from zipfile import ZipFile
import json
import os
from typing import Dict
from mcdreforged.api.all import Metadata, Serializable


class SerializableMetadata(Serializable, Metadata):
    version: str
    dependencies: Dict[str, str]


if __name__ == '__main__':
    self = os.path.dirname(__file__)
    if os.path.isdir(self):
        with open('mcdreforged.plugin.json', 'r', encoding='UTF-8') as f:
            meta = SerializableMetadata.deserialize(json.load(f))
    else:
        with ZipFile(self) as f:
            meta = SerializableMetadata.deserialize(json.loads(f.read('mcdreforged.plugin.json')))
    exe = os.path.basename(sys.executable)
    help_msg = """
============= {2} v{3} =============
<prefix> is the command you run this program
<prefix> init-motd <file>    Initialize JoinMOTD file
<prefix> init-schedule <file>    Initialize schedule for a generated config
<prefix> init-extra <file>    Initialize an extra config file
""".strip().format(exe[:-4] if exe.endswith('.exe') else exe, self, meta.name, meta.version)
    if len(sys.argv) == 3:
        cmd, file = sys.argv[1], sys.argv[2]
        if cmd == 'init-motd':
            sys.exit(init_default_motd(file))
        elif cmd == 'init-schedule':
            sys.exit(init_schedule(file))
        elif cmd == 'init-extra':
            sys.exit(init_extra_config(file))
    print(help_msg)