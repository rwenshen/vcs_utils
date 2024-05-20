from abc import ABC, abstractmethod
from pathlib import Path


class Repo(ABC):

    def __init__(self, root: Path):
        self.__root = root

    @property
    def root(self) -> Path:
        return self.__root


class RepoRemoteInterface(ABC):
    pass


class RepoReadInterface(ABC):
    pass


class RepoWriteInterface(ABC):
    pass