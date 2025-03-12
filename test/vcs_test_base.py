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

    validNextOpDict = {
        'add': ('edit', 'delete', 'move', 'move_edit'),
        'edit': ('edit', 'delete', 'move', 'move_edit'),
        'delete': ('add', 'move_dest'),
        'move': ('add', 'move_dest', 'move_back', 'move_back_edit'),
        'move_edit': ('add', 'move_dest', 'move_back', 'move_back_edit'),
        'move_dest': ('edit', 'delete', 'move', 'move_edit'),
        'move_back': ('edit', 'delete', 'move', 'move_edit'),
        'move_back_edit': ('edit', 'delete', 'move', 'move_edit'),
    }

    __opResultDict = {
        frozenset(('add', 'edit')): 'add',
        frozenset(('add', 'delete')): 'none',
        frozenset(('add', 'move')): 'none',
        frozenset(('add', 'move_edit')): 'none',

        frozenset(('edit', 'edit')): 'edit',
        frozenset(('edit', 'delete')): 'delete',
        frozenset(('edit', 'move')): 'move_edit',
        frozenset(('edit', 'move_edit')): 'move_edit',

        frozenset(('delete', 'add')): 'edit',
        frozenset(('delete', 'move_dest')): 'edit',

        frozenset(('move', 'add')): 'edit',
        frozenset(('move', 'move_dest')): 'edit',
        frozenset(('move', 'move_back')): 'edit',

        frozenset(('move_dest', 'edit')): 'move_dest',
        frozenset(('move_dest', 'delete')): 'none',
        frozenset(('move_dest', 'move')): 'none',

        frozenset(('none', 'add')): 'add',
        frozenset(('none', 'move_dest')): 'move_dest',
    }

    def ttt():

        opChains = []
        chainLength = 5
        moveTmpFiles = []
        moveDestTmpFiles = []
        def iterChains(op, chain):
            if len(chain) > 1:
                yield chain
            if len(chain) < chainLength:
                for nextOp in validNextOpDict[op]:
                    yield from iterChains(nextOp, (*chain, nextOp))

        for op in validNextOpDict.keys():
            for chain in iterChains(op, (op,)):
                for opi in chain:
                    if op == 'move_dest':
                        index = len(moveTmpFiles)
                        moveTmpFiles.append(f'move_tmp{index}')
                opChains.append((*chain, '-'.join(chain)))