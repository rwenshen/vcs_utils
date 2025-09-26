from enum import Enum, auto
import typing
from abc import ABC, abstractmethod

from ..vcs.logger import *
from .change import Change, ChangeErrorCode

if typing.TYPE_CHECKING:
    from .repo import Repo

class CommitErrorCode(Enum):
    # commit error category
    writable = ChangeErrorCode.last.value
    readonly = auto()
    wrong_depot = auto()
    already_saved = auto()
    nothing_to_save = auto()
    not_saved = auto()
    already_submitted = auto()

    last = auto()

VcsHelperError.registerError('common', ErrorCategory.commit,
    CommitErrorCode.writable, VcsHelperError.ErrorLevel.error,
    'Commit "{description}" must be writable!')
VcsHelperError.registerError('common', ErrorCategory.commit,
    CommitErrorCode.readonly, VcsHelperError.ErrorLevel.error,
    'Commit "{description}" must be readonly!')
VcsHelperError.registerError('common', ErrorCategory.commit,
    CommitErrorCode.already_saved, VcsHelperError.ErrorLevel.error,
    'Commit "{description}" has been saved! The saving is skipped.')
VcsHelperError.registerError('common', ErrorCategory.commit,
    CommitErrorCode.nothing_to_save, VcsHelperError.ErrorLevel.error,
    'Commit "{description}" is empty, nothing to be saved!')
VcsHelperError.registerError('common', ErrorCategory.commit,
    CommitErrorCode.not_saved, VcsHelperError.ErrorLevel.error,
    'Submission of commit "{description}" failed! It has NOT been saved!')
VcsHelperError.registerError('common', ErrorCategory.commit,
    CommitErrorCode.already_submitted, VcsHelperError.ErrorLevel.error,
    'Submission of commit "{description}" failed! It has been submitted!')

class Commit(ABC):
    ''' A commit.
Commit.commitRef is VCS specific data in python (e.g. change spec in P4Python, \
or git.Commit / git.Index in GitPython).
Commit.vcsData is VCS specific data (e.g. changelist number in P4, or commit \
SHA in Git).'''
    
    def __init__(self, repo: 'Repo', commitRef: typing.Any):
        self.__repo = repo
        self.__commitRef = commitRef
        self.__commonCommitError = VcsHelperError(
                                                'common', ErrorCategory.commit)
        self.__lastIterResult = 0

    @property
    def error(self):
        return self.__commonCommitError

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
    def vcsData(self) -> typing.Any:
        raise NotImplemented

    @property
    @abstractmethod
    def author(self) -> str:
        raise NotImplemented

    @property
    @abstractmethod
    def email(self) -> str:
        raise NotImplemented

    def __verifyStatus(self, status: bool, expected: bool, 
            errorCode: CommitErrorCode, **kwargs) -> bool:
        if expected != status:
            if self.__commonCommitError.raiseError(errorCode, **kwargs):
                return False
        return True

    @property
    @abstractmethod
    def isWritable(self) -> bool:
        raise NotImplemented

    def verifyWritable(self) -> bool:
        return self.__verifyStatus(self.isWritable, True,
                            CommitErrorCode.writable,
                            description=self.description.replace('\n', '\\n'))

    def verifyReadOnly(self) -> bool:
        return self.__verifyStatus(self.isWritable, False,
                            CommitErrorCode.readonly,
                            description=self.description.replace('\n', '\\n'))

    @property
    @abstractmethod
    def hasSaved(self) -> bool:
        raise NotImplemented

    @property
    @abstractmethod
    def isEmpty(self) -> bool:
        raise NotImplemented

    def verifySavable(self) -> bool:
        return \
            self.__verifyStatus(self.hasSaved, False,
                    CommitErrorCode.already_saved,
                    description=self.description.replace('\n', '\\n')) and \
            self.__verifyStatus(self.isEmpty, False,
                    CommitErrorCode.nothing_to_save,
                    description=self.description.replace('\n', '\\n'))

    @property
    @abstractmethod
    def hasSubmitted(self) -> bool:
        raise NotImplemented

    def verifySubmittable(self) -> bool:
        return \
            self.__verifyStatus(self.hasSaved, True,
                    CommitErrorCode.not_saved,
                    description=self.description.replace('\n', '\\n')) and \
            self.__verifyStatus(self.isEmpty, False,
                    CommitErrorCode.nothing_to_save,
                    description=self.description.replace('\n', '\\n')) and \
            self.__verifyStatus(self.hasSubmitted, False,
                    CommitErrorCode.already_submitted,
                    description=self.description.replace('\n', '\\n'))

    def changeFile(self, change: Change) -> bool:
        if not self.verifyWritable():
            return False
        return self.changeFileImpl(change)

    @abstractmethod
    def changeFileImpl(self, change: Change) -> bool:
        raise NotImplemented

    def save(self, message: str) -> bool:
        if not self.verifySavable():
            return False
        return self.saveImpl(message)
    
    @abstractmethod
    def saveImpl(self, message: str) -> bool:
        raise NotImplemented

    def submit(self, message: str|None = None) -> bool:
        if not self.hasSaved:
            if message is None:
                message = "<New Commit>"
            if not self.save(message):
                return False
        if not self.verifySubmittable():
            return False
        return self.submitImpl()

    @abstractmethod
    def submitImpl(self) -> bool:
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
