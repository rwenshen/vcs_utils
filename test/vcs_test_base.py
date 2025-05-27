import unittest
from pathlib import Path
import shutil
import logging
import sys
import os
import stat
import typing
from abc import ABC, abstractmethod

from .._common.logger import *
from .._common.change import ChangeType, Change
from .._common.commit import Commit, CommitErrorCode
from .._common.repo import Repo


class VCSTestBase(unittest.TestCase, ABC):

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

        cls.__commitTestAddedList: typing.List[int|str] = []
        cls.__vcsName: str = 'Unknown'

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        VcsHelperLogger.info(self.id())

    @property
    def repo(self) -> Repo:
        raise NotImplementedError

    @property
    def vcsName(self) -> str:
        return self.__class__.__vcsName

    @property
    def commitTestAddedList(self)-> typing.List[int|str]:
        return self.__class__.__commitTestAddedList
    
    def __getErrorCode(self, isCommon: bool, category: ErrorCategory,
                                                    errorCode: int) -> int:
        vcsName = 'common' if isCommon else self.vcsName
        return VcsHelperError.calcErrorCode(vcsName, category, errorCode)

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

    def assertSave(self, repo: Repo, commit: Commit, message: str):
        result = commit.save(message)
        self.assertEqual(result, 0)

    def assertSubmit(self, repo: Repo, commit: Commit):
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, repo.getTopCommit())

    def assertSaveSubmit(self, repo: Repo, commit: Commit, message: str):
        result = commit.save(message)
        self.assertEqual(result, 0)
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, repo.getTopCommit())

    def assertFailure(self, fn: typing.Callable[[], int],
            isCommon: bool, category: ErrorCategory, errorCode: int,
            raiseTypes: typing.Iterable[VcsHelperError.RaiseType] = (
                VcsHelperError.RaiseType.exception,
                VcsHelperError.RaiseType.return_code
            )):
        errorCode = self.__getErrorCode(isCommon, category, errorCode)
        # failure with exception
        if VcsHelperError.RaiseType.exception in raiseTypes:
            VcsHelperError.raiseType = VcsHelperError.RaiseType.exception
            with self.assertRaises(VcsHelperException) as context:
                fn()
                self.assertTrue(context.exception.code, errorCode)
        # failure with return code
        if VcsHelperError.RaiseType.return_code in raiseTypes:
            VcsHelperError.raiseType = VcsHelperError.RaiseType.return_code
            result = fn()
            self.assertEqual(result, errorCode)

    # test case implementations
    __fileNames = [
        'a@1%2#3.txt',
        'b@1%2#3.txt',
        'c@1%2#3.txt',
    ]
    @staticmethod
    def __getTextFileContent(fileName: str) -> str:
        return 'Hello txt '+ Path(fileName).stem

    def implTest_commit_initCommit(self, repo: Repo):
        fileName = VCSTestBase.__fileNames[0]
        content = VCSTestBase.__getTextFileContent(fileName)
        message = 'Init commit.'
        VcsHelperLogger.info('[TEST] Add %s...', fileName)
        # new commit
        commit = repo.getNewCommit()
        self.assertTrue(commit.isWritable)
        # empty commit
        self.assertFailure(lambda: commit.save(message),
            True, ErrorCategory.commit, CommitErrorCode.nothing_to_save.value)
        self.assertIsNone(self.repo.getTopCommit())
        # add
        self.checkAddFile(commit, fileName, content)
        # save (git commit to local branch)
        self.assertSaveSubmit(self.repo, commit, message)
        self.commitTestAddedList.append(commit.vcsData)

    def implTest_commit_writableCommit(self, repo: Repo):
        fileName = VCSTestBase.__fileNames[0]
        VcsHelperLogger.info('[TEST] Test writable commit...')
        commit = repo.getTopCommit()
        change = Change(Path(fileName), ChangeType.edit, changeContent='tmp')
        self.assertFailure(lambda: commit.changeFile(change),
            True, ErrorCategory.commit, CommitErrorCode.writable.value)

    def implTest_commit_saveCommitSkip(self, repo: Repo):
        fileName = VCSTestBase.__fileNames[1]
        content = VCSTestBase.__getTextFileContent(fileName)
        message = 'The 2nd commit.'
        VcsHelperLogger.info('[TEST] Skip commit save, add %s...', fileName)
        # empty commit
        commit = repo.getNewCommit()
        self.assertFailure(lambda: commit.save(message),
            True, ErrorCategory.commit, CommitErrorCode.nothing_to_save.value)
        self.checkAddFile(commit, fileName, content)
        # first save
        self.assertSave(repo, commit, message)
        # second save, skip
        self.assertFailure(lambda: commit.save(message),
            True, ErrorCategory.commit, CommitErrorCode.already_saved.value)
        # submit
        self.assertSubmit(repo, commit)
        self.commitTestAddedList.append(commit.vcsData)

    def implTest_commit_directlySubmit(self, repo: Repo):
        fileName = VCSTestBase.__fileNames[1]
        content = VCSTestBase.__getTextFileContent(fileName) + ', 2nd'
        message = f'Edit {fileName}'
        VcsHelperLogger.info('[TEST] Submit directly, edit %s...', fileName)
        commit = repo.getNewCommit()
        result = commit.changeFile(Change(
            Path(fileName), ChangeType.edit, changeContent=content))
        self.assertEqual(result, 0)
        result = commit.submit(message)
        self.assertEqual(result, 0)
        self.assertEqual(commit, repo.getTopCommit())
        self.commitTestAddedList.append(commit.vcsData)

    def implTest_commit_submissionFailure(self,
            # function to create commit which will be failed to be submitted
            createCommitFn: typing.Callable[[], typing.Tuple[Commit]],
            isCommon: bool, category: ErrorCategory, errorCode: int):
        VcsHelperLogger.info('[TEST] Submission Failure...')
        commit = createCommitFn()
        self.assertFailure(commit.submit, isCommon, category, errorCode)

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