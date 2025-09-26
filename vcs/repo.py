from enum import Enum, auto
from pathlib import Path
import typing
from abc import ABC, abstractmethod

from .logger import *
from .commit import Commit


class RepoErrorCode(Enum):
    # repo error category
    root_unset = 1
    root_inexistent = auto()

    last = auto()

VcsHelperError.registerError('common', ErrorCategory.repo,
    RepoErrorCode.root_unset, VcsHelperError.ErrorLevel.fatal,
    'Repo root hasn\'t been set!')

VcsHelperError.registerError('common', ErrorCategory.repo,
    RepoErrorCode.root_inexistent, VcsHelperError.ErrorLevel.fatal,
    'Repo root "{root}" should exists!')


class Repo(ABC):
    class SubmissionType(Enum):
        submit_per_save = auto()
        submit_multiple_saves = auto()

    @staticmethod
    def verifyRoot(func):
        def wrapper(self, *args, **kwargs):
            error = VcsHelperError('common', ErrorCategory.repo)
            if self.root is None:
                return error.raiseError(
                        RepoErrorCode.root_unset)
            if not self.root.exist():
                return error.raiseError(
                        RepoErrorCode.root_inexistent, root=self.root)
            return func(self, *args, **kwargs)
        return wrapper

    def __init__(self, root: Path):
        self.__root = root
        self.__lastIterResult = 0

    @property
    def lastIterResult(self) -> int:
        return self.__lastIterResult
    @lastIterResult.setter
    def lastIterResult(self, value: bool):
        self.__lastIterResult = value

    @property
    def root(self) -> Path:
        return self.__root

    @property
    @abstractmethod
    def submissionType(self) -> SubmissionType:
        raise NotImplemented

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplemented

    @abstractmethod
    def clone(self, root: Path, force: bool=False, **kwargs) -> bool:
        raise NotImplemented

    @abstractmethod
    def sync(self, commit: Commit|None=None,
            reset: bool=False) -> bool:
        raise NotImplemented

    @abstractmethod
    def clearPending(self) -> bool:
        raise NotImplemented

    @abstractmethod
    def getCommit(self, vcsCommitInfo) -> Commit|None:
        raise NotImplemented

    @abstractmethod
    def getNewCommit(self) -> Commit|None:
        raise NotImplemented

    @abstractmethod
    def getTopCommit(self) -> Commit|None:
        raise NotImplemented

    @abstractmethod
    def getCommitFromTag(self, tagName: str) -> Commit|None:
        raise NotImplemented

    @abstractmethod
    def setTag(self, tagName: str, commit: Commit, message: str) -> bool:
        raise NotImplemented

    @abstractmethod
    def deleteTag(self, tagName: str) -> bool:
        raise NotImplemented

    @abstractmethod
    def getTagMessage(self, tagName: str) -> str|None:
        raise NotImplemented

    @abstractmethod
    def iterCommits(self, after: Commit|None = None
            ) -> typing.Iterator[Commit]:
        raise NotImplemented

    @abstractmethod
    def submit(self, commit: Commit) -> bool:
        raise NotImplemented
