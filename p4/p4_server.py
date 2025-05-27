from pathlib import Path
import subprocess
from P4 import P4

from .p4_runner import *
from .._common.logger import *

class P4Server:

    def __init__(self, root: Path, user: str='admin', port: str='1666'):
        self._p4d: subprocess.Popen|None = None
        self._p4: P4|None = None
        
        # verify p4d
        p4dCmd = None
        try:
            subprocess.check_output('p4d -h')
            p4dCmd = 'p4d'
        except:
            pass
        try:
            subprocess.check_output(r'C:\Program Files\Perforce\DVCS\p4d.exe -h')
            p4dCmd = r'C:\Program Files\Perforce\DVCS\p4d.exe'
        except:
            pass
        if p4dCmd is None:
            VcsHelperLogger.critical('Cannot find p4d.exe! Make sure its path is in PATH.')
            exit(1)
        
        if not root.exists() or not root.joinpath('.p4root').exists():
            root.mkdir(parents=True, exist_ok=True)

        # start
        print([p4dCmd, '-r', str(root), '-p', port])
        self._p4d = subprocess.Popen([p4dCmd, '-r', str(root), '-p', port])

        # add user
        self._p4 = P4()
        self._p4.port = port
        self._p4.user = user
        self._p4.client = 'not_set'
        self._p4.connect()
        assert self._p4.connected()

    def __del__(self):
        if self._p4d is not None:
            self._p4d.terminate()
            self._p4d.communicate()
        if self._p4 is not None and self._p4.connected():
            self._p4.disconnect()

    @property
    def p4(self) -> P4:
        if self._p4 is None:
            raise RuntimeError('P4 connection is not established.')
        return self._p4
