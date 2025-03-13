from pathlib import Path
import unittest

from .vcs_test_base import VCSTestBase
from ..common.logger import *
from ..common.change import ChangeType, Change
from ..common.commit import CommitErrorCode
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

    # init repo / clone repo 
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
            f' at {str(sub1TmpRoot)}.')
        self.__class__.repo = GitRepo.cloneRepo(
            sub1TmpRoot, gitRemoteSubList[0])

    # commits
    def test_02_01_initCommit(self):
        # common init commit
        self.implTest_commit_initCommit(self.repo)

        # single writable commit
        commit = self.repo.getNewCommit('1')
        self.assertTrue(commit.isWritable)
        c = self.repo.getNewCommit('2')
        self.assertIsNone(c)
        # git commit author and email
        authorName = 'test'
        authorEmail = 'test@test'
        self.repo.setAuthor(authorName, authorEmail)
        self.assertEqual(commit.author, authorName)
        self.assertEqual(commit.email, authorEmail)
        del commit

    def test_02_02_writableCommit(self):
        # common test
        self.implTest_commit_writableCommit(self.repo)
        # git reset local commit (saved commit)
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
        self.implTest_commit_saveCommitSkip(self.repo)

    def test_02_04_directlySubmit(self):
        self.implTest_commit_directlySubmit(self.repo)

#    def test_02_05_clearPending(self):
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


# TODO submodule