from enum import Enum, auto
from dataclasses import dataclass
import typing


@dataclass
class VcsUtilsResult:
    class _Result(Enum):
        SUCCESS = auto()
        ERROR = auto()

    _result: _Result
    result_data: typing.Any = None
    error: int = 0

    @classmethod
    def create_success(cls, data: typing.Any = None):
        return cls(VcsUtilsResult._Result.SUCCESS, result_data=data)

    @classmethod
    def create_error(cls, error: int):
        return cls(VcsUtilsResult._Result.ERROR, error=error)

    @classmethod
    def copy_error(cls, vcs_result: 'VcsUtilsResult'):
        if vcs_result._result != VcsUtilsResult._Result.ERROR:
            raise ValueError('copy_error requires a VcsUtilsResult with error result')
        return cls(VcsUtilsResult._Result.ERROR, error=vcs_result.error)

    def __bool__(self) -> bool:
        return self._result == VcsUtilsResult._Result.SUCCESS
