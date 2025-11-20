from enum import Enum, auto
from pathlib import Path
from dataclasses import dataclass

from .logger import *


class ChangeErrorCode(Enum):
    path_absolute = 0x1000 # 0-0xfff, reserved for vcs specific
    add_existent_file = auto()
    nothing_to_apply = auto()
    nothing_to_apply_for_delete = auto()

    last = auto()

VcsErrorManager.registerError('common', ErrorCategory.commit,
    ChangeErrorCode.path_absolute, VcsErrorManager.ErrorLevel.error,
    '"{path}" is absolute.\nPath in change must be relative!')
VcsErrorManager.registerError('common', ErrorCategory.commit,
    ChangeErrorCode.add_existent_file, VcsErrorManager.ErrorLevel.error,
    'Trying to add an existent file "{path}"!')
VcsErrorManager.registerError('common', ErrorCategory.commit,
    ChangeErrorCode.nothing_to_apply, VcsErrorManager.ErrorLevel.warning,
    'Nothing to apply for "{change_desc}"! Skipped.')
VcsErrorManager.registerError('common', ErrorCategory.commit,
    ChangeErrorCode.nothing_to_apply_for_delete, VcsErrorManager.ErrorLevel.warning,
    'Nothing to apply for "{change_desc}"! Skipped.')


@dataclass
class VcsResultChange(VcsResult):
    def __post_init__(self):
        if bool(self.result):
            assert isinstance(self.resultData, Change)


class ChangeType(Enum):
    ''' Type of a change.'''

    add = auto()
    delete = auto()
    edit = auto()
    move = auto()


class Change:
    ''' Hold a file change.
All path should be relative.
- filePath: relative file path to change
- changeType: ChangeType[add, delete, edit, move]
- destPath: relative file path for the destination of move
- changeContent: content to apply to file to be changed, current support full
    content only
'''

    def __verifyPath(self, path: Path) -> VcsResult:
        errorManager = VcsErrorManager('common', ErrorCategory.commit)
        if path.is_absolute():
            return errorManager.raiseError(
                    ChangeErrorCode.path_absolute, path=str(path))
        return VcsResult.createSuccess()

    @staticmethod
    def createAddChange(filePath: Path,
            changeContent: bytearray|None=None) -> VcsResultChange:
        change = Change()
        verifyResult = change.__verifyPath(filePath)
        if not verifyResult:
            return VcsResultChange.copyError(verifyResult)
        change.__path = filePath
        change.__changeType = ChangeType.add
        change.__fullContent = changeContent
        return VcsResultChange.createSuccess(change)

    @staticmethod
    def createDeleteChange(filePath: Path) -> VcsResultChange:
        change = Change()
        verifyResult = change.__verifyPath(filePath)
        if not verifyResult:
            return VcsResultChange.copyError(verifyResult)
        change.__path = filePath
        change.__changeType = ChangeType.delete
        return VcsResultChange.createSuccess(change)

    @staticmethod
    def createEditChange(filePath: Path,
            changeContent: bytearray|None=None) -> VcsResultChange:
        change = Change()
        verifyResult = change.__verifyPath(filePath)
        if not verifyResult:
            return VcsResultChange.copyError(verifyResult)
        change.__path = filePath
        change.__changeType = ChangeType.edit
        change.__fullContent = changeContent
        return VcsResultChange.createSuccess(change)

    @staticmethod
    def createMoveChange(filePath: Path, destPath: Path,
            changeContent: bytearray|None=None) -> VcsResultChange:
        change = Change()
        verifyResult = change.__verifyPath(filePath)
        if not verifyResult:
            return VcsResultChange.copyError(verifyResult)
        verifyResult = change.__verifyPath(destPath)
        if not verifyResult:
            return VcsResultChange.copyError(verifyResult)
        change.__path = filePath
        change.__changeType = ChangeType.move
        change.__destPath = destPath
        change.__fullContent = changeContent
        return VcsResultChange.createSuccess(change)

    def __init__(self): 
        self.__path = Path()
        self.__changeType = ChangeType.add
        self.__destPath = None
        self.__fullContent = None

    def __str__(self):
        return f'<Change {self.description}>'

    def applyChangeContent(
            self, absPath: Path, destAbsPath: Path=Path()) -> VcsResult:
        errorManager = VcsErrorManager('common', ErrorCategory.commit)
        
        if self.changeType == ChangeType.delete:
            return errorManager.raiseError(
                                ChangeErrorCode.nothing_to_apply_for_delete,
                                change_desc=str(self))

        if self.__fullContent is None:
            errorManager.raiseError(
                ChangeErrorCode.nothing_to_apply,
                change_desc=str(self))
            return False

        if self.changeType == ChangeType.add:
            try:
                absPath.touch(exist_ok=False)
            except:
                return errorManager.raiseError(
                                ChangeErrorCode.add_existent_file, path=absPath)

        if self.changeType == ChangeType.move:
            destAbsPath.write_bytes(self.__fullContent)
        else:
            absPath.write_bytes(self.__fullContent)
        return VcsResult.createSuccess()

    #def addParent(self, parent: Path):
    #    if parent == Path():
    #        return # no root, just skip
    #    self.__verifyPath(parent)
    #    self.__path = parent.joinpath(self.__path)
    #    if self.__destPath is not None:
    #        self.__destPath = parent.joinpath(self.__destPath)

    #def removeParent(self, parent: Path):
    #    if parent == Path():
    #        return # no root, just skip
    #    self.__verifyPath(parent)
    #    if parent not in self.__path.parents:
    #        # TODO: error handling
    #        VcsHelperLogger.warning(f'Skip removing parent!\n"{str(parent)}" '\
    #            f'is not a parent of "{str(self.__path)}"')
    #        return
    #    self.__path = self.__path.relative_to(parent)
    #    if self.__destPath is not None:
    #        assert parent in self.__destPath.parents
    #        self.__destPath = self.__destPath.relative_to(parent)

    #def cloneChange(self,
    #        addParent: Path=Path(),
    #        removeParent: Path=Path()) -> 'Change|None':
    #    
    #    change = Change()
    #    change.__path = self.path
    #    change.__changeType = self.changeType
    #    change.__destPath = self.destPath
    #    return change
    #    if addParent != Path():
    #        change.addParent(addParent)
    #        assert removeParent == Path()
    #    elif removeParent != Path():
    #        change.removeParent(removeParent)
    #    return change

    @property
    def description(self) -> str:
        s = f'{self.changeType.name} {self.path}'
        if self.changeType == ChangeType.move:
            s += f' to {self.destPath}'
        return s

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def changeType(self) -> ChangeType:
        return self.__changeType

    @property
    def destPath(self) -> Path|None:
        return self.__destPath
