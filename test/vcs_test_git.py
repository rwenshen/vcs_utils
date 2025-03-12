import unittest
from pathlib import Path
import shutil

from rs_utils.vcs_helper.git.git_repo import GitRepoErrorCode

from .vcs_test_base import VCSTestBase
from ..common.logger import *
from ..common.commit import CommitErrorCode
from ..git import *


gitTestRoot = Path(r'.\output\vcs_test_git')
gitLocalRemote = gitTestRoot.joinpath('remote')
localDepotRoot = gitTestRoot.joinpath('local')


class GitRepoTest(VCSTestBase):

    @classmethod
    def setUpClass(cls):
        super(GitRepoTest, cls).setUpClass()
        gitTestRoot.mkdir(exist_ok=True, parents=True)
        cls.remoteRepo = None
        cls.repo = None

    @classmethod
    def tearDownClass(cls):
        #shutil.rmtree(str(gitTestRoot))
        super(GitRepoTest, cls).tearDownClass()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_01_1_createRepo(self):
        VcsHelperLogger.info(f'Create git repository at {str(gitLocalRemote)}.')
        self.__class__.remoteRepo = GitRepo.initRepo(gitLocalRemote, bare=True)

    def test_01_2_cloneRepo(self):
        VcsHelperLogger.info(f'Clone git repository from {str(gitLocalRemote)}'\
            f' at {str(localDepotRoot)}.')
        self.__class__.repo = GitRepo.cloneRepo(localDepotRoot, gitLocalRemote)
