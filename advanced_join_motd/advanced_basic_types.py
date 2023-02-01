from typing import Union
from mcdreforged.api.rtext import RTextBase


class AdvancedInteger(int):
    @property
    def digits_list(self):
        return [int(num) for num in list(str(self))]

    def __len__(self):
        return len(self.digits_list)

    def __getitem__(self, item: Union[str, int, float]):
        ind = int(item)
        return 0 if (ind >= 0 and ind + 1 > len(self)) or (ind < 0 and abs(ind) > len(self)) else self.digits_list[ind]

    @property
    def ordinal(self) -> str:
        if self[-2] == 1:
            return f'{self}th'
        elif self[-1] not in (1, 2, 3):
            return f'{self}th'
        elif self[-1] == 1:
            return f'{self}st'
        elif self[-1] == 2:
            return f'{self}nd'
        elif self[-1] == 3:
            return f'{self}rd'
        else:
            return str(self)


class AdvancedList(list):
    def __repr__(self):
        to_join = []
        for item in self:
            if not isinstance(item, RTextBase):
                item = str(item)
            to_join.append(item)
        if any(map(lambda x: isinstance(x, RTextBase), to_join)):
            return RTextBase.join(', ', to_join)
        else:
            return ', '.join(to_join)
