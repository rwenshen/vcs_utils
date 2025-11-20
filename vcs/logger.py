import logging
from enum import Enum, auto
from dataclasses import dataclass
import typing


__all__ = [
    'VcsHelperLogger',
    'ErrorCategory',
    'VcsHelperException',
    'VcsResult',
    'VcsErrorManager',
]


class VcsHelperLogger:

    __logger = logging.getLogger(f'rs.vcs')

    @staticmethod
    def getLogger():
        return VcsHelperLogger.__logger

    @staticmethod
    def __log(func, msg: str, *args, **kwargs):
        func(msg, *args, **kwargs)

    @staticmethod
    def debug(msg: str, *args, **kwargs):
        func = VcsHelperLogger.__logger.debug
        VcsHelperLogger.__log(func, msg, *args, **kwargs)

    @staticmethod
    def info(msg: str, *args, **kwargs):
        func = VcsHelperLogger.__logger.info
        VcsHelperLogger.__log(func, msg, *args, **kwargs)

    @staticmethod
    def warning(msg: str, *args, **kwargs):
        func = VcsHelperLogger.__logger.warning
        VcsHelperLogger.__log(func, msg, *args, **kwargs)

    @staticmethod
    def error(msg: str, *args, **kwargs):
        func = VcsHelperLogger.__logger.error
        VcsHelperLogger.__log(func, msg, *args, **kwargs)

    @staticmethod
    def critical(msg: str, *args, **kwargs):
        func = VcsHelperLogger.__logger.critical
        VcsHelperLogger.__log(func, msg, *args, **kwargs)


class ErrorCategory(Enum):

    ungrouped = 0
    repo = auto()
    connection = auto()
    remote = auto()
    commit = auto()
    tag = auto()


class VcsHelperException(BaseException):
    def __init__(self, code: int=0, message: str=''):
        self.code: int = code
        self.message: str = message

    def __str__(self):
        if hasattr(self, 'code') and hasattr(self, 'message'):
            return f'VcsHelperError({self.code:02x}, "{self.message}")'
        return super().__str__()

    def __eq__(self, other):
        return self.code == other.code

@dataclass
class VcsResult:
    class Result(Enum):
        success = auto()
        error = auto()

    result: Result
    resultData: typing.Any = None
    error: int = 0

    @classmethod
    def createSuccess(cls, data: typing.Any = None):
        return cls(VcsResult.Result.success, resultData=data)
    @classmethod
    def createError(cls, error: int):
        return cls(VcsResult.Result.error, error=error)
    @classmethod
    def copyError(cls, vcsResult: 'VcsResult'):
        assert vcsResult.result == VcsResult.Result.error
        return cls(VcsResult.Result.error, error=vcsResult.error)

    def bool(self):
        return self.result == VcsResult.Result.success

class VcsErrorManager:

    class ErrorLevel(Enum):
        warning = auto()    # warning, continue current operation
        error = auto()      # error, exit current operation
        fatal = auto()      # fatal error, raise exception or exit directly

    class RaiseType(Enum):
        exception = auto()
        exit_code = auto()

    @dataclass
    class ErrorDefinition:
        category: ErrorCategory
        code: int
        level: 'VcsErrorManager.ErrorLevel'
        messageFormat: str

    raiseType = RaiseType.exception

    __registeredVcs = {
        'common': 0,
    }

    __registeredErrors = {}

    @staticmethod
    def registerVcs(vcsName: str, index: int):
        assert vcsName not in VcsErrorManager.__registeredVcs
        assert index not in VcsErrorManager.__registeredVcs.values()
        assert index > 0 and index <= 0xff
        VcsErrorManager.__registeredVcs[vcsName] = index

    @staticmethod
    def registerError(vcsName: str, category: ErrorCategory,
            errorCode: int|Enum, errorLevel: ErrorLevel,
            messageFormat: str):
        errorDict = VcsErrorManager.__registeredErrors.setdefault(vcsName, {})
        errorDict = errorDict.setdefault(category, {})
        _errorCode = errorCode.value if isinstance(errorCode, Enum) else errorCode
        assert _errorCode not in errorDict
        assert _errorCode > 0 and _errorCode <= 0xffff
        errorDict[_errorCode] = VcsErrorManager.ErrorDefinition(
            category=category,
            code=_errorCode,
            level=errorLevel,
            messageFormat=messageFormat
        )

    @staticmethod
    def calcErrorCode(vcsName: str, category: ErrorCategory, errorCode: int):
        assert vcsName in VcsErrorManager.__registeredVcs, \
            'Unregistered VCS {vcsName}!'
        assert errorCode > 0 and errorCode <= 0xffff
        return (VcsErrorManager.__registeredVcs[vcsName] << 24) | \
            (category.value << 16) | errorCode

    def __init__(self, vcsName: str, category: ErrorCategory):
        assert vcsName in VcsErrorManager.__registeredVcs, \
            'Unregistered VCS {vcsName}!'

        self.__errorCode = VcsErrorManager.__registeredVcs[vcsName] << 24
        self.__errorCode |= category.value << 16
        self.__errorDict = VcsErrorManager.__registeredErrors\
                                .get(vcsName, {}).get(category, {})

    # Raise errors:
    #   warning: log warning message, return False (means continue current operation)
    #   error: log error message, return True (means exit current operation)
    #   fatal: log error message, raise exception or exit directly
    def raiseError(self, errorCode: int|Enum, **kwargs) -> VcsResult:
        exception = VcsHelperException()
        _errorCode: int = errorCode.value if isinstance(errorCode, Enum)\
                                        else errorCode
        if _errorCode in self.__errorDict:
            errorDef = self.__errorDict[_errorCode]
            exception.code = self.__errorCode | errorDef.code
            try:
                exception.message = errorDef.messageFormat.format(**kwargs)
            except:
                exception.message = f'Unformatted: "{errorDef.messageFormat}"'
            errorLevel = errorDef.level
        else:
            exception.code = _errorCode
            exception.message = 'Unregistered error!'
            errorLevel = VcsErrorManager.ErrorLevel.fatal # treat as fatal
        
        match errorLevel:
            case VcsErrorManager.ErrorLevel.warning:
                VcsHelperLogger.warning(exception.message)
                return VcsResult.createSuccess()
            case VcsErrorManager.ErrorLevel.error:
                VcsHelperLogger.error(exception.message)
                return VcsResult.createError(exception.code)
            case VcsErrorManager.ErrorLevel.fatal:
                VcsHelperLogger.critical(exception.message)
                if VcsErrorManager.raiseType == VcsErrorManager.RaiseType.exception:
                    raise exception
                else:
                    exit(exception.code)
            case _:
                assert False, 'Unknown error level!'
