from pathlib import Path
import unittest

from .vcs_test_base import VCSTestBase
from ..vcs.logger import *
from ..vcs.change import ChangeType, Change
from ..vcs.commit import Commit, CommitErrorCode
from ..vcs.git import *
from ..vcs.git.git_commit import GitCommitErrorCode
from ..vcs.git.git_repo import GitRepoErrorCode


gitTestRoot = Path(r'.\output\vcs_test_git')
gitRemote = gitTestRoot.joinpath('remote')
gitRemoteSubList = [
    gitTestRoot.joinpath('remote_sub1'),
    gitTestRoot.joinpath('remote_sub2'),
    gitTestRoot.joinpath('remote_sub3'),
]
localDepotRoot = gitTestRoot.joinpath('local')
sub1TmpRoot = gitTestRoot.joinpath('local_sub1')
sub1TmpRoot2 = gitTestRoot.joinpath('local_sub1_2')

sub1Root = gitTestRoot.joinpath('sub1')
sub2Root = gitTestRoot.joinpath('dirSub/sub2')
subSubRoot = gitTestRoot.joinpath('sub3')


class GitRepoTest(VCSTestBase):

    testRoot = gitTestRoot

    @classmethod
    def setUpClass(cls):
        super(GitRepoTest, cls).setUpClass()
        cls.vcsName = 'git'
        cls.remoteRepo = None
        cls.remoteSubRepoList = []
        cls.repo = None
        cls.repo2 = None

    @classmethod
    def tearDownClass(cls):
        super(GitRepoTest, cls).tearDownClass()

    @property
    def repo(self) -> GitRepo:
        return self.__class__.repo
    @property
    def repo2(self) -> GitRepo:
        return self.__class__.repo2

    # common assert
    def assertCheckoutCommit(self, commit: Commit):
        result = self.repo.checkoutCommit(commit)
        self.assertEqual(result, 0)
        self.assertTrue(self.repo.isHeadDetached)
        self.assertEqual(commit, self.repo.getHeadCommit())

    def assertCheckoutHead(self, branchName: str):
        result = self.repo.checkoutHead(branchName)
        self.assertEqual(result, 0)
        self.assertFalse(self.repo.isHeadDetached)
        self.assertEqual(self.repo.getTopCommit(), self.repo.getHeadCommit())

    def assertTrackingBranch(self, trackingBranchPath: str|None):
        result = self.repo.setTrackingBranchPath(trackingBranchPath)
        self.assertEqual(result, 0)
        self.assertFalse(self.repo.isHeadDetached)
        self.assertEqual(trackingBranchPath, self.repo.trackingBranchPath)

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
        self.__class__.repo2 = GitRepo.cloneRepo(
            sub1TmpRoot2, gitRemoteSubList[0])

    # commits
    def test_02_01_initCommit(self):
        authorName = 'user1'
        authorEmail = 'user1@test.com'
        self.repo.setAuthorNameAndEmail(authorName, authorEmail)
        
        # common init commit
        self.implTest_commit_initCommit(self.repo)

        # git commit author and email
        commit = self.repo.getCommit(self.commitTestAddedList[0])
        self.assertEqual(commit.author, authorName)
        self.assertEqual(commit.email, authorEmail)

        commit = self.repo.getNewCommit()
        authorName = 'user2'
        authorEmail = 'user2@test.com'
        self.repo.setAuthorNameAndEmail(authorName, authorEmail)
        self.assertEqual(commit.author, authorName)
        self.assertEqual(commit.email, authorEmail)

    def test_02_02_writableCommit(self):
        self.implTest_commit_writableCommit(self.repo)

    def test_02_03_saveCommitSkip(self):
        self.implTest_commit_saveCommitSkip(self.repo)

    def test_02_04_directlySubmit(self):
        self.implTest_commit_directlySubmit(self.repo)

    def test_02_05_01_checkoutCommit(self):
        self.assertFalse(self.repo.isHeadDetached)
        # readonly commit
        commit = self.repo.getNewCommit()
        self.assertFailure(lambda: self.repo.checkoutCommit(commit),
                    True, ErrorCategory.commit, CommitErrorCode.readonly.value)
        # do check out
        commit = self.repo.getCommit(self.commitTestAddedList[1])
        self.assertCheckoutCommit(commit)
        commit = self.repo.getCommit(self.commitTestAddedList[0])
        self.assertCheckoutCommit(commit)
        self.assertCheckoutCommit(commit)

    def test_02_05_02_checkoutHead(self):
        # check out head
        self.assertFailure(lambda: self.repo.checkoutHead('inexistent'),
                            False, ErrorCategory.repo,
                            GitRepoErrorCode.check_out_head_inexistent.value)
        self.assertCheckoutHead('release')
        self.assertCheckoutHead('release')

    def test_02_05_03_newHead(self):
        pass

    def test_02_05_04_renameHead(self):
        pass

    def test_02_05_06_trackingBranch(self):
        # head detached
        commit = self.repo.getCommit(self.commitTestAddedList[0])
        self.assertCheckoutCommit(commit)
        self.assertFailure(lambda: self.repo.setTrackingBranchPath(None),
                                        False, ErrorCategory.remote,
                                        GitRepoErrorCode.head_detached.value)
        self.assertCheckoutHead('release')
        # invalid remote
        self.assertFailure(
            lambda: self.repo.setTrackingBranchPath('inexistent/release'),
                                    False, ErrorCategory.remote,
                                    GitRepoErrorCode.remote_inexistent.value)
        # inexistent head
        self.assertFailure(
            lambda: self.repo.setTrackingBranchPath('origin/inexistent'),
                                False, ErrorCategory.remote,
                                GitRepoErrorCode.remote_branch_inexistent.value)
        # tracking branch
        self.assertTrackingBranch(None)
        self.assertTrackingBranch(None)
        self.assertTrackingBranch('origin/release')
        self.assertTrackingBranch('origin/release')

    @unittest.skip("skip")
    def test_02_05_06_submissionFailure(self):
        # test save empty commit
        def createEmptyCommit():
            return self.repo.getNewCommit('Unused changelist')
        self.implTest_commit_submissionFailure(createEmptyCommit,
            ErrorCategory.commit, CommitErrorCode.nothing_to_save.value)
        # test checkout commit / head function first
        commit = self.repo.getNewCommit('Unused changelist')
        self.assertFailure(lambda: self.repo.checkoutCommit(commit),
                        ErrorCategory.commit, CommitErrorCode.writable.value)

# git reset local commit (saved commit)
        localCommit = self.repo.getLocalCommit()
        commit = self.repo.getNewCommit('tmp')
        result = commit.changeFile(
            Change(Path('a.txt'), ChangeType.edit, changeContent='tmp'))
        self.assertEqual(result, 0)
        result = commit.save()
        self.assertEqual(result, 0)
        self.assertEqual(commit, self.repo.getLocalCommit())
        result = commit.changeFile(
            Change(Path('b.txt'), ChangeType.edit, changeContent='tmp'))
        self.assertNotEqual(result, 0)
        result = self.repo.sync(localCommit, reset=True)
        self.assertEqual(result, 0)
        self.assertEqual(localCommit, self.repo.getLocalCommit())

        # test push non top local

        # test
        #def createEditCommit():
        #    commit = self.repo.getNewCommit('Unused changelist')
        #    result = commit.changeFile(
        #        Change(Path('b@1%2#3.txt'), ChangeType.edit))
        #    self.assertEqual(result, 0)
        #def createCommit():
        #    commit = self.repo.getNewCommit('Unused changelist')
        #    result = commit.changeFile(
        #        Change(Path('b@1%2#3.txt'), ChangeType.edit))
        #    self.assertEqual(result, 0)
        #    # shelve
        #    result = commit.save()
        #    self.assertEqual(result,0)
        #    root = clientRoot
        #    txtB = root.joinpath('b@1%2#3.txt')
        #    result = p4Run(self.repo.p4, 'shelve', getP4ValidLocalPath(txtB), **{
        #        '-c': commit.vcsData,
        #    })
        #    self.assertEqual(result, 0)
        #    return commit
        #errorCode = (1 << 24) | (ErrorCategory.remote.value << 16) \
        #                    | P4RunErrorCode.submit.value
        #self.implTest_commit_submissionFailure(createCommit, errorCode)

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


# TODO fetch, multiple remote
# TODO branch / remote branch
# TODO submodule
# TODO remote