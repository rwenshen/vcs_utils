from enum import Enum, auto
import typing
from abc import ABC, abstractmethod

from .logger import *
from .change import Change, ChangeErrorCode


class CommitErrorCode(Enum):
    # commit error category
    writable = ChangeErrorCode.last.value
    readonly = auto()
    wrongDepot = auto()

    last = auto()


VcsHelperError.registerError('common',
            ErrorCategory.commit, CommitErrorCode.writable,
            'Commit "{description}" must be writable!')
VcsHelperError.registerError('common',
            ErrorCategory.commit, CommitErrorCode.readonly,
            'Commit "{description}" must be readonly!')


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
    def repo(self):
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
    def vcsData(self):
        raise NotImplemented

    @property
    @abstractmethod
    def author(self) -> str:
        raise NotImplemented

    @property
    @abstractmethod
    def email(self) -> str:
        raise NotImplemented

    @property
    @abstractmethod
    def isWritable(self) -> bool:
        raise NotImplemented

    @staticmethod
    def checkWritable(exceptionOrExit: bool=False,
            returnResult=VcsHelperError.RaiseType.return_code):
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                if not self.isWritable:
                    return self.__commonCommitError.raiseError(
                            CommitErrorCode.writable,
                            description=self.description.replace('\n', '\\n'),
                            exceptionOrExit=exceptionOrExit,
                            returnResult=returnResult)
                return func(self, *args, **kwargs)
            return wrapper
        return decorator

    @staticmethod
    def checkReadonly(exceptionOrExit: bool=False,
            returnResult=VcsHelperError.RaiseType.return_code):
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                if self.isWritable:
                    return self.__commonCommitError.raiseError(
                            CommitErrorCode.readonly,
                            description=self.description.replace('\n', '\\n'),
                            exceptionOrExit=exceptionOrExit,
                            returnResult=returnResult)
                return func(self, *args, **kwargs)
            return wrapper
        return decorator

    @abstractmethod
    def changeFile(self, change: Change) -> int:
        raise NotImplemented

    @abstractmethod
    def save(self) -> int:
        raise NotImplemented

    @abstractmethod
    def submit(self) -> int:
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
