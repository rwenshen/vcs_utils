import unittest
from pathlib import Path
import shutil
import logging
import sys
import os
import stat

from ..common.logger import VcsHelperLogger


class VCSTestBase(unittest.TestCase):

    testRoot = Path(r'.\output\vcs_test')

    @classmethod
    def setUpClass(cls):
        if cls.testRoot.exists():
            def del_rw(action, name, exc):
                os.chmod(name, stat.S_IWRITE)
                os.remove(name)
            shutil.rmtree(str(cls.testRoot), onerror=del_rw)

        stdoutHandler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('[%(levelname)s] %(message)s')
        stdoutHandler.setFormatter(formatter)
        VcsHelperLogger.getLogger().level= logging.DEBUG
        VcsHelperLogger.getLogger().addHandler(stdoutHandler)

    @classmethod
    def tearDownClass(cls):
        pass
