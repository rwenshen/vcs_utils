import unittest
from pathlib import Path
import shutil
import logging
import sys
import os
import stat

from ..common.logger import *
from ..common.change import ChangeType, Change
from ..common.commit import Commit, CommitErrorCode
from ..common.repo import Repo


class VCSTestBase(unittest.TestCase):

    testRoot = Path(r'.\output\vcs_test')

    @classmethod
    def setUpClass(cls):
        if cls.testRoot.exists():
            def del_rw(function, name, exc):
                os.chmod(name, stat.S_IWRITE)
                os.remove(name)
            shutil.rmtree(str(cls.testRoot), onexc=del_rw)

        stdoutHandler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('[%(levelname)s] %(message)s')
        stdoutHandler.setFormatter(formatter)
        VcsHelperLogger.getLogger().level= logging.DEBUG
        VcsHelperLogger.getLogger().addHandler(stdoutHandler)

    @classmethod
    def tearDownClass(cls):
        pass

    # common functions
    def checkAddFile(self, commit: Commit, fileName: str, content: str,
            localRoot: Path | None = None, parent: Path | None=None) -> Path:
        txtFile = Path(fileName)
        if parent is not None and parent is not None:
            root = localRoot.joinpath(parent)
            root.mkdir(exist_ok=True, parents=True)
            txtFile = parent.joinpath(fileName)

        result = commit.changeFile(
            Change(txtFile, ChangeType.add, changeContent = content))
        self.assertEqual(result, 0)
        return txtFile

    def checkDeleteFile(self, commit, fileName: str,
            localRoot: Path, parent: Path | None=None) -> Path:
        root = localRoot
        if parent is not None:
            root = root.joinpath(parent)
        txtFile = root.joinpath(fileName)
        self.assertTrue(txtFile.exists())
        result = commit.changeFile(
            Change(txtFile.relative_to(localRoot), ChangeType.delete))
        self.assertEqual(result, 0)
        self.assertFalse(txtFile.exists())
        return txtFile

    def assertSaveSubmit(self, repo: Repo, commit: Commit):
        result = commit.save()
        self.assertEqual(result, 0)
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, repo.getTopCommit())

    # test case implementations
    __fileNames = [
        'a@1%2#3.txt',
        'b@1%2#3.txt',
        'c@1%2#3.txt',
    ]
    def __getTextFileContent(fileName: str) -> str:
        return 'Hello txt '+ Path(fileName).stem

    def implTest_commit_initCommit(self, repo: Repo):
        fileName = VCSTestBase.__fileNames[0]
        content = VCSTestBase.__getTextFileContent(fileName)
        VcsHelperLogger.info('[TEST] Add %s...', fileName)
        # new commit
        commit = repo.getNewCommit('Init commit.')
        self.assertTrue(commit.isWritable)
        result = commit.save()
        self.assertNotEqual(result, 0)
        self.assertIsNone(self.repo.getTopCommit())
        # add
        self.checkAddFile(commit, fileName, content)
        # save (git commit to local branch)
        self.assertSaveSubmit(self.repo, commit)
        # clear
        del commit

    def implTest_commit_writableCommit(self, repo: Repo):
        fileName = VCSTestBase.__fileNames[0]
        VcsHelperLogger.info('[TEST] Test writable commit...')
        commit = repo.getTopCommit()
        result = commit.changeFile(
            Change(Path(fileName), ChangeType.edit, changeContent='tmp'))
        errorCode = (ErrorCategory.commit.value << 16) | CommitErrorCode.writable.value
        self.assertEqual(result, errorCode)
        # clear
        del commit

    def implTest_commit_saveCommitSkip(self, repo: Repo):
        fileName = VCSTestBase.__fileNames[1]
        content = VCSTestBase.__getTextFileContent(fileName)
        VcsHelperLogger.info('[TEST] Skip commit save, add %s...', fileName)
        commit = repo.getNewCommit('The 2nd commit.')
        result = commit.save()
        self.assertNotEqual(result, 0)
        self.checkAddFile(commit, fileName, content)
        result = commit.save()
        self.assertEqual(result, 0)
        result = commit.save()
        self.assertNotEqual(result, 0)
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, repo.getTopCommit())
        # clear
        del commit

    def implTest_commit_directlySubmit(self, repo: Repo):
        fileName = VCSTestBase.__fileNames[1]
        content = VCSTestBase.__getTextFileContent(fileName) + ', 2nd'
        VcsHelperLogger.info('[TEST] Submit directly, edit %s...', fileName)
        commit = repo.getNewCommit(f'Edit {fileName}')
        result = commit.changeFile(Change(
            Path(fileName), ChangeType.edit, changeContent=content))
        self.assertEqual(result, 0)
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, repo.getTopCommit())
        # clear
        del commit

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