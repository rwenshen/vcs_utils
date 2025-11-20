from enum import Enum, auto
from pathlib import Path
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .logger import *
from .commit import Commit, VcsResultCommit


class RepoErrorCode(Enum):
    # repo error category
    root_unset = 1
    root_inexistent = auto()

    last = auto()

VcsErrorManager.registerError('common', ErrorCategory.repo,
    RepoErrorCode.root_unset, VcsErrorManager.ErrorLevel.fatal,
    'Repo root hasn\'t been set!')

VcsErrorManager.registerError('common', ErrorCategory.repo,
    RepoErrorCode.root_inexistent, VcsErrorManager.ErrorLevel.fatal,
    'Repo root "{root}" should exists!')


@dataclass
class VcsResultRepo(VcsResult):
    def __post_init__(self):
        if bool(self.result):
            assert isinstance(self.resultData, Repo)

@dataclass
class VcsResultCommitList(VcsResult):
    def __post_init__(self):
        if bool(self):
            assert isinstance(self.resultData, typing.Iterable)
            for item in self.resultData:
                assert isinstance(item, Commit)

class Repo(ABC):
    """
Base class for a version control repository abstraction.
Contains interface for common repository operations (with branch operations,
but without remote operations).,
This class provides core repository operations for single-root, local-only
workflows.
"""
    __invalidRootPath = Path('<invalid>')

    def verifyRoot(self):
        if self.root == Repo.__invalidRootPath:
            self.__errorManagerCommon.raiseError(RepoErrorCode.root_unset)
        if not self.root.exists():
            self.__errorManagerCommon.raiseError(
                    RepoErrorCode.root_inexistent, root=self.root)

    def __init__(self, root: Path|None = None):
        if root is None:
            self.__root = Repo.__invalidRootPath
        else:
            self.__root = root
        self.__lastIterResult = 0
        self.__errorManagerCommon = VcsErrorManager(
                                                'common', ErrorCategory.repo)

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
    def description(self) -> str:
        raise NotImplemented

    # commit interfaces

    def resolveCommit(self, commitData:Commit|int|bytes|str|None
            )-> VcsResultCommit:
        if isinstance(commitData, Commit):
            return VcsResultCommit.createSuccess(commitData)
        elif commitData is None:
            return self.getHeadCommit()
        elif isinstance(commitData, str):
            return self.getCommitFromTag(commitData)
        else:
            return self.getCommit(commitData)

    @abstractmethod
    def getCommit(self, vcsData: int|bytes) -> VcsResultCommit:
        raise NotImplemented

    @abstractmethod
    def getHeadCommit(self) -> VcsResultCommit:
        raise NotImplemented

    @abstractmethod
    def getCommitFromTag(self, tagName: str) -> VcsResultCommit:
        raise NotImplemented

    @abstractmethod
    def newCommit(self) -> VcsResultCommit:
        raise NotImplemented

    def iterCommits(self,
                toCommitData: Commit|int|bytes|str|None, # none means head commit
                fromCommitData: Commit|int|bytes|str|None, # None means initial commit
            ) -> VcsResultCommitList:
        toCommitResult = self.resolveCommit(toCommitData)
        if not toCommitResult:
            return VcsResultCommitList.copyError(toCommitResult.error)
        toCommit = toCommitResult.resultData
        
        if fromCommitData is not None:
            fromCommitResult = self.resolveCommit(fromCommitData)
            if not fromCommitResult:
                return VcsResultCommitList.copyError(fromCommitResult.error)
            fromCommit = fromCommitResult.resultData
        else:
            fromCommit = None 

        return self.iterCommitsImpl(toCommit, fromCommit)

    @abstractmethod
    def iterCommitsImpl(self,
                toCommit: Commit,
                fromCommit: Commit|None, # None means from initial commit
            ) -> VcsResultCommitList:
        raise NotImplemented

    # sync to commit
    # Acts as git reset --hard / --mixed
    # - reset=True: --hard, discard working dir changes
    # - reset=False: --mixed, keep working dir changes
    def sync(self, commit: Commit|int|str|None=None,
            reset: bool=False) -> VcsResult:
        self.verifyRoot()

        if isinstance(commit, Commit):
            toBeSynced = commit
        else:
            commitResult = self.getCommit(commit)
            if not commitResult:
                return VcsResult.copyError(commitResult)
            toBeSynced = commitResult.resultData

        return self.syncImpl(toBeSynced, reset)

    @abstractmethod
    def syncImpl(self, commit: Commit, reset: bool) -> VcsResult:
        raise NotImplemented

    @abstractmethod
    def reset(self) -> VcsResult:
        raise NotImplemented

    # tag interfaces
    @abstractmethod
    def setTag(self, tagName: str, commit: Commit, message: str) -> VcsResult:
        raise NotImplemented

    @abstractmethod
    def deleteTag(self, tagName: str) -> VcsResult:
        raise NotImplemented

    @abstractmethod
    def getTagMessage(self, tagName: str) -> VcsResult:
        raise NotImplemented

    @abstractmethod
    def submit(self, commit: Commit) -> VcsResult:
        raise NotImplemented
    
    # remote interfaces

    @property
    @abstractmethod
    def remoteSupport(self) -> bool:
        raise NotImplemented

    @abstractmethod
    @classmethod
    def init(cls, root: Path, **kwargs) -> VcsResultRepo:
        raise NotImplemented

    @abstractmethod
    def clone(self, newRoot: Path, **kwargs) -> VcsResultRepo:
        raise NotImplemented
