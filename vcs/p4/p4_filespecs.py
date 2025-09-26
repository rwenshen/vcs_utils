from dataclasses import dataclass
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
import re


class P4PathSpec:
    def __init__(self, filePath: Path, isEscaped: bool=False):
        # filePath should be a pathlib.Path, but allow str for flexibility
        pathStr = str(filePath).replace('\\', '/')
        if isEscaped:
            self.__unescaped = self.unescape(pathStr)
            self.__escaped = pathStr
        else:
            self.__unescaped = pathStr
            self.__escaped = self.escape(pathStr)

    @property
    def unescaped(self):
        return self.__unescaped

    @property
    def escaped(self):
        return self.__escaped

    @staticmethod
    def escape(path: str) -> str:
        replacements = {
            '#': '%23',
            '@': '%40',
            re.compile('(?<!%)%(?!%)'): '%25',
        }
        for from_str, to_str in replacements.items():
            if isinstance(from_str, str):
                path = path.replace(from_str, to_str)
            else:  # regex
                path = from_str.sub(to_str, path)
        return path

    @staticmethod
    def unescape(path: str) -> str:
        replacements = {
            '%23': '#',
            '%40': '@',
            '%25': '%',
        }
        for from_str, to_str in replacements.items():
            path = path.replace(from_str, to_str)
        return path

@dataclass
class P4VersionSpec(ABC):
    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError

@dataclass
class P4VersionSpecRevision(P4VersionSpec):
    revision: int

    def __post_init__(self):
        assert self.revision >= 0, "Revision number must be non-negative"

    def __str__(self) -> str:
        return f'#{self.revision}'

@dataclass
class P4VersionSpecNoneRevision(P4VersionSpec):
    def __str__(self) -> str:
        return '#none'

@dataclass
class P4VersionSpecHeadRevision(P4VersionSpec):
    def __str__(self) -> str:
        return '#head'

@dataclass
class P4VersionSpecHaveRevision(P4VersionSpec):
    def __str__(self) -> str:
        return '#have'

@dataclass
class P4VersionSpecChangelist(P4VersionSpec):
    changelist: int
    at: bool = False

    def __post_init__(self):
        assert self.changelist > 0, "Changelist number must be positive"

    def __str__(self) -> str:
        if self.at:
            return f'@={self.changelist}'
        else:
            return f'@{self.changelist}'

@dataclass
class P4VersionSpecLabel(P4VersionSpec):
    label: str

    def __post_init__(self):
        assert self.label, "Label cannot be empty"

    def __str__(self) -> str:
        return f'@{self.label}'

@dataclass
class P4VersionSpecClient(P4VersionSpec):
    client: str

    def __post_init__(self):
        assert self.client, "Client name cannot be empty"

    def __str__(self) -> str:
        return f'@{self.client}'

@dataclass
class P4VersionSpecDate(P4VersionSpec):
    date: datetime

    def __str__(self) -> str:
        # Perforce format: yyyy/mm/dd:hh:mm:ss
        return f'@{self.date.strftime("%Y/%m/%d:%H:%M:%S")}'


class P4FileSpec:

    def __init__(self, pathSpec: P4PathSpec, versionSpec: P4VersionSpec|None=None):
        self.__pathSpec = pathSpec
        self.__versionSpec = versionSpec

    @property
    def path(self) -> Path:
        return Path(self.__pathSpec.unescaped)
    
    @property
    def unescaped(self) -> str:
        return self.__pathSpec.unescaped + \
                        (str(self.__versionSpec) if self.__versionSpec else '')
    @property
    def escaped(self) -> str:
        return self.__pathSpec.escaped + \
                        (str(self.__versionSpec) if self.__versionSpec else '')
