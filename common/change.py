from enum import Enum, auto
from pathlib import Path
import typing

from .logger import *


class ChangeErrorCode(Enum):
    path_absolute = 0x1000 # 0-0xfff, reserved for vcs specific
    missing_destination = auto()
    add_existent_file = auto()

    last = auto()


VcsHelperError.registerError('common',
    ErrorCategory.commit, ChangeErrorCode.path_absolute,
    '"{path}" is absolute.\nPath in change must be relative!')
VcsHelperError.registerError('common',
    ErrorCategory.commit, ChangeErrorCode.missing_destination,
    'Missing destination for a move change!')
VcsHelperError.registerError('common',
    ErrorCategory.commit, ChangeErrorCode.add_existent_file,
    'Trying to add an existent file "{path}"!')


class ChangeType(Enum):
    ''' Type of a change.'''

    add = auto()
    delete = auto()
    edit = auto()
    move = auto()


class Change:
    ''' A file change.
All path should be relative.
filePath: relative file path to change
changeType: ChangeType[add, delete, edit, move]
destPath: relative file path for the destination of move
changeContent: content to apply to file to be changed, current support full content only'''

    def __checkPath(self, path: typing.Optional[Path]):
        error = VcsHelperError('common', ErrorCategory.commit)
        if path is not None and path.is_absolute():
            error.raiseError(ChangeErrorCode.path_absolute,
                                    exceptionOrExit=True, path=str(path))

    def __init__(self, filePath: Path, changeType: ChangeType,
            destPath: typing.Optional[Path]=None, # for move
            changeContent: typing.Optional[str]=None,
            ): 
        error = VcsHelperError('common', ErrorCategory.commit)
        self.__path = filePath
        self.__changeType = changeType
        self.__destPath = destPath
        self.__checkPath(filePath)
        self.__checkPath(destPath)
        if changeType == ChangeType.move and destPath is None:
            error.raiseError(ChangeErrorCode.missing_destination,
                                    exceptionOrExit=True)
        self.__fullContent = changeContent

    def __str__(self):
        return f'<Change {self.description}>'

    def applyChange(self, absPath: Path, destAbsPath: typing.Optional[Path]):
        error = VcsHelperError('common', ErrorCategory.commit)

        if self.__fullContent is None:
            return 0

        if self.changeType == ChangeType.delete:
            VcsHelperLogger.warning(
                "callable in change won't be called for delete!")
            return 0

        if self.changeType == ChangeType.add:
            try:
                absPath.touch(exist_ok=False)
            except:
                return error.raiseError(
                    ChangeErrorCode.add_existent_file, path=absPath) 

        if self.changeType == ChangeType.move:
            destAbsPath.write_text(self.__fullContent)
        else:
            absPath.write_text(self.__fullContent)

        return 0

    def addParent(self, parent: Path):
        if parent == Path():
            return
        self.__checkPath(parent)
        self.__path = parent.joinpath(self.__path)
        if self.__destPath is not None:
            self.__destPath = parent.joinpath(self.__destPath)

    def removeParent(self, parent: Path):
        if parent == Path():
            return
        self.__checkPath(parent)
        if parent not in self.__path.parents:
            VcsHelperLogger.warning(f'Skip removing parent!\n"{str(parent)}" '\
                f'is not a parent of "{str(self.__path)}"')
            return
        self.__path = self.__path.relative_to(parent)
        if self.__destPath is not None:
            assert parent in self.__destPath.parents
            self.__destPath = self.__destPath.relative_to(parent)

    def clone(self,
            addParent: typing.Optional[Path]=Path(),
            removeParent: typing.Optional[Path]=Path()) -> 'Change':
        change = Change(self.path, self.changeType, self.destPath)
        if addParent != Path():
            change.addParent(addParent)
            assert removeParent == Path()
        elif removeParent != Path():
            change.removeParent(removeParent)
        return change

    @property
    def description(self) -> str:
        s = f'{self.changeType.name} {self.path}'
        if self.changeType == ChangeType.move:
            s += f' to {self.destPath}'
        return s

    @property
    def path(self):
        return self.__path

    @property
    def changeType(self):
        return self.__changeType

    @property
    def destPath(self):
        return self.__destPath
