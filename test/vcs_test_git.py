from pathlib import Path
import unittest

from .vcs_test_base import VCSTestBase
from ..logger import *
from ..change import ChangeType, Change
from ..commit import CommitErrorCode
from ..git import *


gitTestRoot = Path(r'.\output\vcs_test_git')
gitRemote = gitTestRoot.joinpath('remote')
gitRemoteSubList = [
    gitTestRoot.joinpath('remote_sub1'),
    gitTestRoot.joinpath('remote_sub2'),
    gitTestRoot.joinpath('remote_sub3'),
]
localDepotRoot = gitTestRoot.joinpath('local')
sub1TmpRoot = gitTestRoot.joinpath('local_sub1')

sub1Root = gitTestRoot.joinpath('sub1')
sub2Root = gitTestRoot.joinpath('dirSub/sub2')
subSubRoot = gitTestRoot.joinpath('sub3')


class GitRepoTest(VCSTestBase):

    testRoot = gitTestRoot

    @classmethod
    def setUpClass(cls):
        super(GitRepoTest, cls).setUpClass()
        cls.remoteRepo = None
        cls.remoteSubRepoList = []
        cls.repo = None

    @classmethod
    def tearDownClass(cls):
        super(GitRepoTest, cls).tearDownClass()

    @property
    def repo(self):
        return self.__class__.repo

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def checkAddFile(self, commit, fileName: str, content: str) -> Path:
        txtFile = Path(fileName)
        result = commit.changeFile(
            Change(txtFile, ChangeType.add, changeContent=content))
        self.assertEqual(result, 0)
        return txtFile

    def test_01_01_createRepo(self):
        VcsHelperLogger.info(f'Create git repository at {str(gitRemote)}.')
        self.__class__.remoteRepo = GitRepo.initRepo(
            gitRemote, bare=True, initialBranch='release')
        for gitRemoteSub in gitRemoteSubList:
            VcsHelperLogger.info(
                f'Create git repository at {str(gitRemoteSub)}.')
            self.__class__.remoteSubRepoList.append(GitRepo.initRepo(
                gitRemoteSub, bare=True, initialBranch='release'))

    def test_01_02_cloneRepo(self):
        VcsHelperLogger.info(f'Clone git repository from {str(gitRemoteSubList[0])}'\
            f' at {str(localDepotRoot)}.')
        self.__class__.repo = GitRepo.cloneRepo(
            sub1TmpRoot, gitRemoteSubList[0])

    # first commit
    def test_02_01_firstCommit(self):
        VcsHelperLogger.info('\nAdd a.txt...')
        # new commit (stage files)
        commit = self.repo.getNewCommit('Init commit.')
        self.assertTrue(commit.isWritable)
        result = commit.save()
        self.assertNotEqual(result, 0)
        # single new commit
        c = self.repo.getNewCommit('tmp')
        self.assertIsNone(c)
        # author
        authorName = 'test'
        authorEmail = 'test@test'
        self.repo.setAuthor(authorName, authorEmail)
        self.assertEqual(commit.author, authorName)
        self.assertEqual(commit.email, authorEmail)
        # add
        self.checkAddFile(commit, 'a.txt', 'Hello txt a')

        # save (git commit to local branch)
        result = commit.save()
        self.assertEqual(result, 0)
        self.assertEqual(commit, self.repo.getCurrentCommit())

        # submit (git push to remote)
        self.assertIsNone(self.repo.getTopCommit())
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, self.repo.getTopCommit())

    def test_02_02_writableCommit(self):
        VcsHelperLogger.info('\nAssert writable commit...')
        commit = self.repo.getTopCommit()
        result = commit.changeFile(
            Change(Path('a.txt'), ChangeType.edit, changeContent='tmp'))
        errorCode = (ErrorCategory.commit.value << 16) | CommitErrorCode.writable.value
        self.assertEqual(result, errorCode)
        # change after save
        currentCommit = self.repo.getCurrentCommit()
        commit = self.repo.getNewCommit('tmp')
        result = commit.changeFile(
            Change(Path('a.txt'), ChangeType.edit, changeContent='tmp'))
        self.assertEqual(result, 0)
        result = commit.save()
        self.assertEqual(result, 0)
        self.assertEqual(commit, self.repo.getCurrentCommit())
        result = commit.changeFile(
            Change(Path('b.txt'), ChangeType.edit, changeContent='tmp'))
        self.assertNotEqual(result, 0)
        result = self.repo.sync(currentCommit, reset=True)
        self.assertEqual(result, 0)
        self.assertEqual(currentCommit, self.repo.getCurrentCommit())

    def test_02_03_saveCommitSkip(self):
        VcsHelperLogger.info('\nSkip commit save, add b.txt...')
        commit = self.repo.getNewCommit('The 2nd commit.')
        result = commit.save()
        self.assertNotEqual(result, 0)
        self.checkAddFile(commit, 'b.txt', 'Hello txt b')
        result = commit.save()
        self.assertEqual(result, 0)
        result = commit.save()
        self.assertNotEqual(result,0)
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, self.repo.getTopCommit())

    def test_02_04_directlySubmit(self):
        VcsHelperLogger.info('\nSubmit directly, edit b.txt...')
        commit = self.repo.getNewCommit('Edit b.txt')
        txtB = Path('b.txt')
        result = commit.changeFile(
            Change(txtB, ChangeType.edit,
                changeContent='Hello txt b, 2nd'
            ))
        self.assertEqual(result, 0)
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, self.repo.getTopCommit())

#    def test_02_06_clearPending(self):
#        VcsHelperLogger.info('\nClear pendings...')
#
#        # create commit
#        commit = self.repo.getNewCommit('default changelist')
#        result = commit.changeFile(
#            Change(Path('a.txt'), ChangeType.edit, changeContent='tmp'))
#        self.assertEqual(result, 0)
#        changes = list(commit.iterChanges())
#        self.assertEqual(len(changes), 1)
#
#        # clear pending files
#        result = self.repo.clearPendings()
#        self.assertEqual(result, 0)
#        changes = list(commit.iterChanges())
#        self.assertEqual(len(changes), 0)
