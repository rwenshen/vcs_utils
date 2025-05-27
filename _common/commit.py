from enum import Enum, auto
import typing
from abc import ABC, abstractmethod

from .logger import *
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


VcsHelperError.registerError('common',
            ErrorCategory.commit, CommitErrorCode.writable,
            'Commit "{description}" must be writable!')
VcsHelperError.registerError('common',
            ErrorCategory.commit, CommitErrorCode.readonly,
            'Commit "{description}" must be readonly!')
VcsHelperError.registerError('common',
            ErrorCategory.commit, CommitErrorCode.already_saved,
            'Commit "{description}" has been saved! The saving is skipped.')
VcsHelperError.registerError('common',
            ErrorCategory.commit, CommitErrorCode.nothing_to_save,
            'Commit "{description}" is empty, nothing to be saved!')
VcsHelperError.registerError('common',
            ErrorCategory.commit, CommitErrorCode.not_saved,
            'Submission of commit "{description}" failed! It has NOT been saved!')
VcsHelperError.registerError('common',
            ErrorCategory.commit, CommitErrorCode.already_submitted,
            'Submission of commit "{description}" failed! It has been submitted!')

class Commit(ABC):
    ''' A commit.
Commit.commitRef is VCS specific data in python (e.g. change spec in P4Python, \
or git.Commit / git.Index in GitPython).
Commit.vcsData is VCS specific data (e.g. changelist number in P4, or commit \
SHA in Git).'''
    
    def __init__(self, repo: 'Repo', commitRef):
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
    def commitRef(self):
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
    def vcsData(self) -> int|str:
        raise NotImplemented

    @property
    @abstractmethod
    def author(self) -> str:
        raise NotImplemented

    @property
    @abstractmethod
    def email(self) -> str:
        raise NotImplemented

    def checkStatus(self, status: bool, expected: bool, 
            errorCode: CommitErrorCode, **kwargs) -> int:
        if expected != status:
            return self.__commonCommitError.raiseError(
                    errorCode, **kwargs)
        return 0

    @property
    @abstractmethod
    def isWritable(self) -> bool:
        raise NotImplemented

    def checkWritable(self, exceptionOrExit: bool=False,
            returnResult=VcsHelperError.RaiseType.return_code) -> int:
        return self.checkStatus(self.isWritable, True,
                            CommitErrorCode.writable,
                            description=self.description.replace('\n', '\\n'),
                            exceptionOrExit=exceptionOrExit,
                            returnResult=returnResult)

    def checkReadOnly(self, exceptionOrExit: bool=False,
            returnResult=VcsHelperError.RaiseType.return_code) -> int:
        return self.checkStatus(self.isWritable, False,
                            CommitErrorCode.readonly,
                            description=self.description.replace('\n', '\\n'),
                            exceptionOrExit=exceptionOrExit,
                            returnResult=returnResult)

    @property
    @abstractmethod
    def hasSaved(self) -> bool:
        raise NotImplemented

    @property
    @abstractmethod
    def isEmpty(self) -> bool:
        raise NotImplemented

    def checkSavable(self) -> int:
        errorCode = self.checkStatus(self.hasSaved, False,
                            CommitErrorCode.already_saved,
                            description=self.description.replace('\n', '\\n'))
        if errorCode != 0:
            return errorCode
        return self.checkStatus(self.isEmpty, False,
                            CommitErrorCode.nothing_to_save,
                            description=self.description.replace('\n', '\\n'))

    @property
    @abstractmethod
    def hasSubmitted(self) -> bool:
        raise NotImplemented

    def checkSubmittable(self) -> int:
        # impossible unsaved
        errorCode = self.checkStatus(self.hasSaved, True,
                            CommitErrorCode.not_saved,
                            description=self.description.replace('\n', '\\n'),
                            exceptionOrExit=True,
                            returnResult=VcsHelperError.RaiseType.exception)
        if errorCode != 0:
            return errorCode
        # check empty
        errorCode = self.checkStatus(self.isEmpty, False,
                            CommitErrorCode.nothing_to_save,
                            description=self.description.replace('\n', '\\n'))
        if errorCode != 0:
            return errorCode
        # check not submitted
        return self.checkStatus(self.hasSubmitted, False,
                            CommitErrorCode.already_submitted,
                            description=self.description.replace('\n', '\\n'))

    def changeFile(self, change: Change) -> int:
        errorCode = self.checkWritable()
        if errorCode != 0:
            return errorCode
        return self.changeFileImpl(change)

    @abstractmethod
    def changeFileImpl(self, change: Change) -> int:
        raise NotImplemented

    def save(self, message: str) -> int:
        errorCode = self.checkSavable()
        if errorCode != 0:
            return errorCode
        return self.saveImpl(message)
    
    @abstractmethod
    def saveImpl(self, message: str) -> int:
        raise NotImplemented

    def submit(self, message: str|None = None) -> int:
        if not self.hasSaved:
            if message is None:
                message = "<New Commit>"
            errorCode = self.save(message)
            if errorCode != 0:
                return errorCode
        errorCode = self.checkSubmittable()
        if errorCode != 0:
            return errorCode
        return self.submitImpl()

    @abstractmethod
    def submitImpl(self) -> int:
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
