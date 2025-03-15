import logging
from enum import Enum, auto
import typing


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
        self.code = code
        self.message = message

    def __str__(self):
        if hasattr(self, 'code') and hasattr(self, 'message'):
            return f'VcsHelperError({self.code:02x}, "{self.message}")'
        return super().__str__()

    def __eq__(self, other):
        return self.code == other.code

class VcsHelperError:

    class RaiseType(Enum):
        exception = auto()
        exit_code = auto()
        return_code = auto()


    raiseType = RaiseType.return_code

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
            errorCode: typing.Union[int, Enum],
            messageFormat: str):
        errorDict = VcsHelperError.__registeredErrors.setdefault(vcsName, {})
        errorDict = errorDict.setdefault(category, {})
        if isinstance(errorCode, Enum):
            errorCode = errorCode.value
        assert errorCode not in errorDict
        assert errorCode > 0 and errorCode <= 0xffff
        errorDict[errorCode] = messageFormat

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

    def raiseError(self, errorCode: typing.Union[int, Enum],
            exceptionOrExit: bool=False,
            returnResult=RaiseType.return_code,
            **kwargs):
        
        exception = VcsHelperException()
        if isinstance(errorCode, Enum):
            errorCode = errorCode.value
        if errorCode in self.__errorDict:
            exception.code = self.__errorCode | errorCode
            try:
                exception.message = self.__errorDict[errorCode].format(**kwargs)
            except:
                exception.message = f'Unformatted: "{self.__errorDict[errorCode]}"'
        else:
            exception.code = errorCode
            exception.message = 'Unregistered error!'
        
        raiseType = VcsHelperError.raiseType
        if exceptionOrExit and raiseType == VcsHelperError.RaiseType.return_code:
            raiseType = VcsHelperError.RaiseType.exception

        VcsHelperLogger.error(exception.message)
        if raiseType == VcsHelperError.RaiseType.exception:
            raise exception
        else:
            if raiseType == VcsHelperError.RaiseType.exit_code:
                exit(exception.code)
            elif returnResult == VcsHelperError.RaiseType.return_code:
                return exception.code
            else:
                return returnResult


class VcsHelperErrorWrapper:

    def __init__(self, vcsName: str, category: ErrorCategory,
            errorCode:  typing.Union[int, Enum], *args, **kwargs):
        self.error = VcsHelperError(vcsName, category)
        self.code = errorCode
        self.args = args
        self.kwargs = kwargs

    def raiseError(self, **kwargs):
        newKwargs = {}
        newKwargs.update(self.kwargs)
        newKwargs.update(kwargs)
        return self.error.raiseError(self.code, *self.args, **newKwargs)
