from enum import Enum, auto
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..vcs.logger import *
from .change import Change, ChangeErrorCode

if typing.TYPE_CHECKING:
    from .repo import Repo

class CommitErrorCode(Enum):
    # commit error category
    writable = ChangeErrorCode.last.value
    readonly = auto()
    wrong_depot = auto()
    already_committed = auto()

    last = auto()

VcsErrorManager.registerError('common', ErrorCategory.commit,
    CommitErrorCode.writable, VcsErrorManager.ErrorLevel.error,
    'Commit "{description}" must be writable!')
VcsErrorManager.registerError('common', ErrorCategory.commit,
    CommitErrorCode.readonly, VcsErrorManager.ErrorLevel.error,
    'Commit "{description}" must be readonly!')
VcsErrorManager.registerError('common', ErrorCategory.commit,
    CommitErrorCode.already_committed, VcsErrorManager.ErrorLevel.error,
    'Failed to commit "{description}"! It has been committed!')


@dataclass
class VcsResultCommit(VcsResult):
    def __post_init__(self):
        if bool(self):
            assert isinstance(self.resultData, Commit)

class Commit(ABC):
    ''' Describe a VCS commit.
Commit.commitRef is VCS specific data in python (e.g. change spec in P4Python, \
or git.Commit / git.Index in GitPython).
Commit.vcsData is VCS specific data (e.g. changelist number in P4, or commit \
SHA in Git).'''
    
    def __init__(self, repo: 'Repo', commitRef):
        self.__repo = repo
        self.__commitRef = commitRef
        self.__errorManagerCommon = VcsErrorManager(
                                                'common', ErrorCategory.commit)
        self.__lastIterResult = 0

    @property
    def errorManager(self):
        return self.__errorManagerCommon

    @property
    def lastIterResult(self) -> int:
        return self.__lastIterResult
    @lastIterResult.setter
    def lastIterResult(self, value: bool):
        self.__lastIterResult = value

    def __eq__(self, other):
        return self.vcsData == other.vcsData

    @property
    def repo(self) -> 'Repo':
        return self.__repo

    @property
    def commitRef(self) -> typing.Any:
        return self.__commitRef
    @commitRef.setter
    def commitRef(self, newRef):
        self.__commitRef = newRef

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplemented

    @property
    @abstractmethod
    def vcsData(self) -> int|bytes:
        raise NotImplemented

    @property
    @abstractmethod
    def author(self) -> str:
        raise NotImplemented

    @property
    @abstractmethod
    def email(self) -> str:
        raise NotImplemented

    def _verifyStatus(self, status: bool, expected: bool, 
            errorCode: CommitErrorCode, **kwargs) -> VcsResult:
        if expected != status:
            return self.__errorManagerCommon.raiseError(errorCode, **kwargs)
        return VcsResult.createSuccess()

    @property
    @abstractmethod
    def isWritable(self) -> bool:
        raise NotImplemented

    def verifyWritable(self) -> VcsResult:
        return self._verifyStatus(self.isWritable, True,
                            CommitErrorCode.writable,
                            description=self.description.replace('\n', '\\n'))

    def verifyReadOnly(self) -> VcsResult:
        return self._verifyStatus(self.isWritable, False,
                            CommitErrorCode.readonly,
                            description=self.description.replace('\n', '\\n'))

    @property
    @abstractmethod
    def isEmpty(self) -> bool:
        raise NotImplemented

    @property
    @abstractmethod
    def hasCommitted(self) -> bool:
        raise NotImplemented

    def verifyCommittable(self) -> VcsResult:
        verifyResult = self._verifyStatus(self.hasCommitted, False,
                        CommitErrorCode.already_committed,
                        description=self.description.replace('\n', '\\n'))
        return verifyResult

    def changeFile(self, change: Change) -> VcsResult:
        verifyResult = self.verifyWritable()
        if not verifyResult:
            return verifyResult
        return self.changeFileImpl(change)

    @abstractmethod
    def changeFileImpl(self, change: Change) -> VcsResult:
        raise NotImplemented

    def commit(self, message: str|None = None) -> VcsResult:
        verifyResult = self.verifyCommittable()
        if not verifyResult:
            return verifyResult
        return self.commitImpl(message)

    @abstractmethod
    def commitImpl(self, message: str|None) -> VcsResult:
        raise NotImplemented

    @abstractmethod
    def iterConflictedChanges(self) -> typing.Iterator[Change]:
        raise NotImplemented

    @abstractmethod
    def iterChanges(self) -> typing.Iterator[Change]:
        raise NotImplemented

    @abstractmethod
    def iterDiffs(self,
            fromCommit: 'Commit') -> typing.Iterator[Change]:
        raise NotImplemented
