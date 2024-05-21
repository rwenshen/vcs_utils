import logging


class VcsHelperLogger:

    __logger = logging.getLogger(f'vcs')

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

    @staticmethod
    def verify(condition: bool, msg: str|None=None, *args, **kwargs):
        if not condition:
            pass