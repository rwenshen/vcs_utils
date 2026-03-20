"""Error handling utilities for vcs_utils.

Provides `VcsUtilsException` and `VcsUtilsErrorManager` for registering
and raising structured error codes and messages.
"""

from enum import Enum, auto
from dataclasses import dataclass
import logging
import typing

from .result import VcsUtilsResult


class ErrorCategory(Enum):
    ungrouped = 0
    repo = auto()
    connection = auto()
    remote = auto()
    commit = auto()
    change = auto()
    tag = auto()


class VcsUtilsException(Exception):
    def __init__(self, code: int = 0, message: str = ''):
        self.code: int = code
        self.message: str = message

    def __str__(self):
        return f'_VcsUtilsException({self.code:02x}, "{self.message}")'

    def __repr__(self) -> str:
        return f"_VcsUtilsException(code={self.code!r}, message={self.message!r})"

    def __eq__(self, other):
        return isinstance(other, VcsUtilsException) and self.code == other.code


class VcsUtilsErrorManager:

    class ErrorLevel(Enum):
        warning = auto()    # warning, continue current operation
        error = auto()      # error, exit current operation
        fatal = auto()      # fatal error, raise exception directly

    @dataclass
    class ErrorDefinition:
        category: ErrorCategory
        code: int
        level: 'VcsUtilsErrorManager.ErrorLevel'
        messageFormat: str

    __registeredVcs: typing.Dict[str, int] = {
        "common": 0,
    }

    __registeredErrors: typing.Dict[str, typing.Dict] = {}

    @staticmethod
    def registerVcs(vcsName: str, index: int):
        if vcsName in VcsUtilsErrorManager.__registeredVcs:
            raise KeyError(f'VCS {vcsName!r} already registered')
        if index in VcsUtilsErrorManager.__registeredVcs.values():
            raise ValueError(f'Index {index!r} already in use')
        if not (0 < index <= 0xFF):
            raise ValueError("index must be in range 1..0xff")
        VcsUtilsErrorManager.__registeredVcs[vcsName] = index

    @staticmethod
    def registerError(
        vcsName: str,
        category: ErrorCategory,
        errorCode: int | Enum,
        errorLevel: ErrorLevel,
        messageFormat: str,
    ):
        errorDict = VcsUtilsErrorManager.__registeredErrors.setdefault(vcsName, {})
        errorDict = errorDict.setdefault(category, {})
        _errorCode = errorCode.value if isinstance(errorCode, Enum) else errorCode

        if _errorCode in errorDict:
            raise KeyError(
                f"Error code {_errorCode!r} already registered for {vcsName!r}/{category}"
            )
        if not (0 < _errorCode <= 0xFFFF):
            raise ValueError("errorCode must be in range 1..0xffff")

        errorDict[_errorCode] = VcsUtilsErrorManager.ErrorDefinition(
            category=category,
            code=_errorCode,
            level=errorLevel,
            messageFormat=messageFormat,
        )

    @staticmethod
    def calcErrorCode(vcsName: str, category: ErrorCategory, errorCode: int):
        if vcsName not in VcsUtilsErrorManager.__registeredVcs:
            raise KeyError(f"Unregistered VCS {vcsName!r}!")
        if not (0 < errorCode <= 0xFFFF):
            raise ValueError("errorCode must be in range 1..0xffff")

        return (
            (VcsUtilsErrorManager.__registeredVcs[vcsName] << 24)
            | (category.value << 16)
            | errorCode
        )

    def __init__(self, vcsName: str, category: ErrorCategory):
        if vcsName not in VcsUtilsErrorManager.__registeredVcs:
            raise KeyError(f'Unregistered VCS {vcsName!r}!')

        self.__errorCode = VcsUtilsErrorManager.__registeredVcs[vcsName] << 24
        self.__errorCode |= category.value << 16
        self.__errorDict = VcsUtilsErrorManager.__registeredErrors\
                                .get(vcsName, {}).get(category, {})

    # Raise errors:
    #   warning: log warning message, return Success (means continue current operation)
    #   error: log error message, return error code (means exit current operation)
    #   fatal: log error message, raise exception directly
    def raiseError(self, logger: logging.Logger, errorCode: int | Enum, **kwargs) -> VcsUtilsResult:
        exception = VcsUtilsException()
        _errorCode: int = errorCode.value if isinstance(errorCode, Enum) else errorCode

        if _errorCode in self.__errorDict:
            errorDef = self.__errorDict[_errorCode]
            exception.code = self.__errorCode | errorDef.code
            try:
                exception.message = errorDef.messageFormat.format(**kwargs)
            except Exception:
                logger.debug('Error formatting message for %r: %s', errorDef, kwargs, exc_info=True)
                exception.message = f'Unformatted: "{errorDef.messageFormat}"'
            errorLevel = errorDef.level
        else:
            # treat unregistered error as fatal with raw code encoded
            exception.code = self.__errorCode | (_errorCode & 0xFFFF)
            exception.message = 'Unregistered error!'
            errorLevel = VcsUtilsErrorManager.ErrorLevel.fatal

        if errorLevel is VcsUtilsErrorManager.ErrorLevel.warning:
            logger.warning(exception.message)
            return VcsUtilsResult.create_success()
        if errorLevel is VcsUtilsErrorManager.ErrorLevel.error:
            logger.error(exception.message)
            return VcsUtilsResult.create_error(exception.code)
        if errorLevel is VcsUtilsErrorManager.ErrorLevel.fatal:
            logger.critical(exception.message)
            raise exception
        raise RuntimeError('Unknown error level!')
