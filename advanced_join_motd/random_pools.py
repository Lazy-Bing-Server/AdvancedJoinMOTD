import os
import random

from advanced_join_motd.utils import random_text_path
from typing import Dict, Optional
from ruamel import yaml


class RandomTextPool(list):
    @property
    def random(self):
        return random.choice(self)


class RandomManager:
    DEFAULT = {
        'original': [
            '武装自己的应该是知识，而不是菠菜公司的烂钱',
            'MCDR小助手提醒您，您今天使用MCDR了吗',
            '挖妮啦小警察出警，听说这里有人not vanilla',
            '笑死，根本学不会',
            '冰冰喵天下第一可爱，不接受反驳'
        ]
    }

    def __init__(self, path: str):
        self.__path = path
        self.__data: Dict[str, RandomTextPool] = {}
        self.load()

    def load(self):
        if not os.path.isfile(self.__path):
            self.init()
        if os.path.isfile(self.__path):
            with open(self.__path, 'r', encoding='UTF-8') as f:
                self.__data = yaml.round_trip_load(f)

    def random(self, pool: Optional[str]):
        return random.choice(self.__data.get(pool, default=[None]))

    def init(self):
        if not os.path.isfile(self.__path):
            with open(self.__path, 'w', encoding='UTF-8') as f:
                yaml.round_trip_dump(self.DEFAULT, f, allow_unicode=True)


random_text_manager = RandomManager(random_text_path)
