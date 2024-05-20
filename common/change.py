from enum import Enum, auto


class ChangeType(Enum):
    ''' Type of a change.'''

    add = auto()
    delete = auto()
    edit = auto()
    move = auto()
