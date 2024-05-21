from abc import ABC, abstractmethod
from pathlib import Path
import typing


class Repo(ABC):

    def __init__(self, root: Path):
        self.__root = root

    @property
    def root(self) -> Path:
        return self.__root
    
    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplemented


class RepoRemoteInterface(ABC):

    @abstractmethod
    @staticmethod
    def clone(root: Path, force: bool=False, **kwargs) -> Repo:
        raise NotImplemented


class RepoReadInterface(ABC):
    pass

class RepoWriteInterface(ABC):
    pass


class RepoTagInterface(ABC):
    pass