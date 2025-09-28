from enum import Enum, auto
from pathlib import Path
import subprocess
from P4 import P4

from ..logger import *


class P4ServerErrorCode(Enum):
    no_executable = auto()
    no_connection = auto()

VcsHelperError.registerError('p4', ErrorCategory.server,
    P4ServerErrorCode.no_executable, VcsHelperError.ErrorLevel.fatal,
    'P4 executable not found! Make sure its path is in PATH.')
VcsHelperError.registerError('p4', ErrorCategory.server,
    P4ServerErrorCode.no_connection, VcsHelperError.ErrorLevel.fatal,
    'Unable to connect to P4 server. Failed to create P4 server.')


class P4Server:

    def __init__(self, root: Path, port: str='1666',
            user: str='admin', description:str='P4 Test Server'):
        self._p4d: subprocess.Popen|None = None
        self._p4: P4|None = None
        self._error = VcsHelperError('p4', ErrorCategory.server)
        
        # verify p4d
        p4dCmd = 'p4d'
        try:
            subprocess.check_output(f'{p4dCmd} -h')
        except:
            self._error.raiseError(P4ServerErrorCode.no_executable)
        
        if not root.exists() or not root.joinpath('.p4root').exists():
            root.mkdir(parents=True, exist_ok=True)

        # start server
        cmdList = [
            p4dCmd,
            '-r', str(root),
            '-p', port,
            '-Id', description
        ]
        VcsHelperLogger.info('Starting P4 server: ' + ' '.join(
            arg if ' ' not in arg else f'"{arg}"' for arg in cmdList))
        self._p4d = subprocess.Popen(cmdList)

        # add user
        self._p4 = P4()
        self._p4.port = f'localhost:{port}'
        self._p4.user = user
        try:
            self._p4.connect()
            assert self._p4.connected()
        except:
            self._error.raiseError(P4ServerErrorCode.no_connection)

    def __del__(self):
        if self._p4d is not None:
            self._p4d.terminate()
            self._p4d.communicate()
        if self._p4 is not None and self._p4.connected():
            self._p4.disconnect()

    @property
    def p4(self) -> P4:
        return self._p4
