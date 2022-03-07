from advanced_join_motd.config import *


def init_default_motd(file: str):
    if os.path.isfile(file):
        raise FileExistsError(file)
    JoinMOTDScheme.init_default(file)


def init_schedule(file: str):
    selected_config = Config.load(file)
    selected_config.init_schedule(file_path=file)


def init_extra_config(file: str):
    if os.path.isfile(file):
        raise FileExistsError(file)
    with open(file, 'w', encoding='UTF-8') as f:
        yaml.round_trip_dump(AdditionalSettings.get_default().serialize(), f, allow_unicode=True)
