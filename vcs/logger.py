import logging
from enum import Enum, auto
from dataclasses import dataclass


__all__ = [
    'VcsHelperLogger',
    'ErrorCategory',
    'VcsHelperException',
    'VcsHelperError',
    'VcsHelperErrorWrapper',
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
    file_stat = auto()
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


class VcsHelperError:

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
        level: 'VcsHelperError.ErrorLevel'
        messageFormat: str

    raiseType = RaiseType.exception
    lastErrorCode: int = 0

    __registeredVcs = {
        'common': 0,
    }

    __registeredErrors = {}

    @staticmethod
    def registerVcs(vcsName: str, index: int):
        assert vcsName not in VcsHelperError.__registeredVcs
        assert index not in VcsHelperError.__registeredVcs.values()
        assert index > 0 and index <= 0xff
        VcsHelperError.__registeredVcs[vcsName] = index

    @staticmethod
    def registerError(vcsName: str, category: ErrorCategory,
            errorCode: int|Enum, errorLevel: ErrorLevel,
            messageFormat: str):
        errorDict = VcsHelperError.__registeredErrors.setdefault(vcsName, {})
        errorDict = errorDict.setdefault(category, {})
        _errorCode = errorCode.value if isinstance(errorCode, Enum) else errorCode
        assert _errorCode not in errorDict
        assert _errorCode > 0 and _errorCode <= 0xffff
        errorDict[_errorCode] = VcsHelperError.ErrorDefinition(
            category=category,
            code=_errorCode,
            level=errorLevel,
            messageFormat=messageFormat
        )

    @staticmethod
    def calcErrorCode(vcsName: str, category: ErrorCategory, errorCode: int):
        assert vcsName in VcsHelperError.__registeredVcs, \
            'Unregistered VCS {vcsName}!'
        assert errorCode > 0 and errorCode <= 0xffff
        return (VcsHelperError.__registeredVcs[vcsName] << 24) | \
            (category.value << 16) | errorCode

    def __init__(self, vcsName: str, category: ErrorCategory):
        assert vcsName in VcsHelperError.__registeredVcs, \
            'Unregistered VCS {vcsName}!'

        self.__errorCode = VcsHelperError.__registeredVcs[vcsName] << 24
        self.__errorCode |= category.value << 16
        self.__errorDict = VcsHelperError.__registeredErrors\
                                .get(vcsName, {}).get(category, {})

    # Raise errors:
    #   warning: log warning message, return False (means continue current operation)
    #   error: log error message, return True (means exit current operation)
    #   fatal: log error message, raise exception or exit directly
    def raiseError(self, errorCode: int|Enum, **kwargs) -> bool:
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
            errorLevel = VcsHelperError.ErrorLevel.fatal # treat as fatal
        
        match errorLevel:
            case VcsHelperError.ErrorLevel.warning:
                VcsHelperLogger.warning(exception.message)
                VcsHelperError.lastErrorCode = exception.code
                return False
            case VcsHelperError.ErrorLevel.error:
                VcsHelperLogger.error(exception.message)
                VcsHelperError.lastErrorCode = exception.code
                return True
            case VcsHelperError.ErrorLevel.fatal:
                VcsHelperLogger.critical(exception.message)
                if VcsHelperError.raiseType == VcsHelperError.RaiseType.exception:
                    raise exception
                else:
                    exit(exception.code)
            case _:
                assert False, 'Unknown error level!'

class VcsHelperErrorWrapper:

    def __init__(self, vcsName: str, category: ErrorCategory,
            errorCode: int|Enum, *args, **kwargs):
        self.error = VcsHelperError(vcsName, category)
        self.code = errorCode
        self.args = args
        self.kwargs = kwargs

    def raiseError(self, **kwargs) -> bool:
        newKwargs = {}
        newKwargs.update(self.kwargs)
        newKwargs.update(kwargs)
        return self.error.raiseError(self.code, *self.args, **newKwargs)
