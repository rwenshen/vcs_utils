from enum import Enum, auto
from pathlib import Path
import typing
from abc import ABC, abstractmethod

from .common.logger import *
from .change import Change
from .commit import Commit


class RepoErrorCode(Enum):
    root_unset = 1
    root_inexistent = auto()


VcsHelperError.registerError('common',
            ErrorCategory.repo, RepoErrorCode.root_unset,
            'Repo root hasn\'t been set!')

VcsHelperError.registerError('common',
            ErrorCategory.repo, RepoErrorCode.root_inexistent,
            'Repo root "{root}" should exists!')


class Repo(ABC):

    class SubmissionType(Enum):
        submit_per_save = auto()
        submit_multiple_saves = auto()

    @staticmethod
    def checkRoot(func):
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
    def clone(self, root: Path, force: bool=False, **kwargs) -> int:
        raise NotImplemented

    @abstractmethod
    def sync(self, commit: typing.Optional[Commit]=None,
            reset: bool=False) -> int:
        raise NotImplemented

    @abstractmethod
    def clearPendings(self) -> int:
        raise NotImplemented

    @abstractmethod
    def getCommit(self, vcsCommitInfo) -> typing.Optional[Commit]:
        raise NotImplemented

    @abstractmethod
    def getNewCommit(self, message: str) -> Commit:
        raise NotImplemented

    @abstractmethod
    def getTopCommit(self) -> Commit:
        raise NotImplemented

    @abstractmethod
    def getCommitFromTag(self, tagName: str) -> typing.Optional[Commit]:
        raise NotImplemented

    @abstractmethod
    def setTag(self, tagName: str, commit: Commit, message: str) -> int:
        raise NotImplemented

    @abstractmethod
    def deleteTag(self, tagName: str) -> int:
        raise NotImplemented

    @abstractmethod
    def getTagMessage(self, tagName: str) -> typing.Optional[str]:
        raise NotImplemented

    @abstractmethod
    def iterCommits(self, after: typing.Optional[Commit] = None
            ) -> typing.Iterator[Commit]:
        raise NotImplemented

    @abstractmethod
    def submit(self, commit: Commit) -> int:
        raise NotImplemented
