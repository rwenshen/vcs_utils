from pathlib import Path
import subprocess
from P4 import P4

from .p4_runner import *
from ..common.logger import *

class P4Server:

    def __init__(self, root: Path, user: str='admin', port: str='1666'):
        self.p4d = None
        self.p4 = None
        
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
        root = str(root)
        print([p4dCmd, '-r', root, '-p', port])
        self.p4d = subprocess.Popen([p4dCmd, '-r', root, '-p', port])

        # add user
        self.p4 = P4()
        self.p4.port = port
        self.p4.user = user
        self.p4.client = 'not_set'
        self.p4.connect()
        assert self.p4.connected()

    def __del__(self):
        if self.p4d is not None:
            self.p4d.terminate()
            self.p4d.communicate()
        if self.p4 is not None and self.p4.connected():
            self.p4.disconnect()
