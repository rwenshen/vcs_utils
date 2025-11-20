from pathlib import Path
import logging
import typing
from os import environ
import platform

#from ..vcs.p4.p4_repo import P4RepoErrorCode

from .vcs_test_base import VCSTestBase
from ..vcs.logger import *
from ..vcs.change import ChangeType, Change
from ..vcs.commit import CommitErrorCode
from ..vcs.repo import Repo
from ..vcs.p4 import *
#from ..vcs.p4.p4_runner import *
#from ..vcs.p4.p4_runner import P4RunErrorCode
from ..vcs.p4.p4_server import P4Server

import unittest

p4TestRoot = Path(r'.\output\vcs_test_p4')
p4LocalServerRoot = p4TestRoot.joinpath('server')
defaultUserName = 'admin'
localDepotName = 'test'
streamDepotName = 'stream_test'
streamMain = f'//{streamDepotName}/main'
streamDev = f'//{streamDepotName}/dev'
clientName = 'client_test'
clientRoot = p4TestRoot.joinpath(clientName).resolve()

class P4RepoTest(VCSTestBase):

    testRoot = p4TestRoot

    @classmethod
    def setUpClass(cls):
        super(P4RepoTest, cls).setUpClass()
        cls._vcsName = 'p4'
        cls._server: P4Server|None = None
#        cls._repo: P4Repo|None = None
        VcsHelperLogger.getLogger().setLevel(logging.INFO)

    @classmethod
    def tearDownClass(cls):
        if cls.server is not None:
            del cls._server
#        if cls.repo is not None:
#            del cls._repo
        super(P4RepoTest, cls).tearDownClass()

    @property
    def server(self) -> P4Server:
        assert self.__class__._server is not None
        return self.__class__._server

#    @property
#    def repo(self) -> Repo:
#        assert self.__class__._repo is not None
#        return self.__class__._repo

#    @property
#    def p4Repo(self) -> P4Repo:
#        assert self.__class__._repo is not None
#        return self.__class__._repo

    # create server and repo
    def test_01_1_createServer(self):
        VcsHelperLogger.info(f'[TEST] Create P4 server at {str(p4LocalServerRoot)}')
        if platform.system() == 'Windows':
            environ['PATH'] = environ.get('PATH','')\
                                            + r';C:\Program Files\Perforce\DVCS'
        else:
            assert False, "TODO: support Linux / MacOS"
        self.__class__._server = P4Server(p4LocalServerRoot, user=defaultUserName)

#    def test_01_2_repoCreate(self):
#        VcsHelperLogger.info(
#            f'[TEST] Create P4 repo {clientName} for user {defaultUserName}')
#        self.__class__._repo = P4Repo(
#                p4Port=self.server.p4.port,
#                p4Client=clientName,
#                p4User=defaultUserName)
#        VcsHelperLogger.info(f'P4Repo "{self.repo.description}" has been created.')
#
#        # no client check
#        errorCode = (1 << 24) | (ErrorCategory.repo.value << 16) \
#                            | P4RepoErrorCode.client_invalid.value
#        with self.assertRaises(VcsHelperException) as context:
#            self.repo.getTopCommit()
#        self.assertTrue(context.exception.code, errorCode)
#
#    def test_01_3_createDepot(self):
#        VcsHelperLogger.info(
#            f'[TEST] Create a new local depot //{localDepotName}/...')
#        result = self.repo.updateSpec('depot', localDepotName, {'-t':'local'})
#        self.assertEqual(result, 0)
#
#        VcsHelperLogger.info(
#            f'[TEST] Create a new stream depot //{streamDepotName}/...')
#        result = self.repo.updateSpec('depot', streamDepotName, {'-t':'stream'})
#        self.assertEqual(result, 0)
#
#        result = p4Run(self.repo.p4, 'depots')
#        if isinstance(result, VcsHelperErrorWrapper):
#            result.raiseError(exceptionOrExit=True)
#        self.assertEqual(len(result), 3)
#
#    def test_01_4_createStream(self):
#        VcsHelperLogger.info(f'[TEST] Create stream {streamMain}')
#        result = self.repo.updateSpec('stream', streamMain, {'-t':'mainline'})
#        self.assertEqual(result, 0)
#
#        VcsHelperLogger.info(f'[TEST] Create stream {streamDev}')
#        result = self.repo.updateSpec('stream', streamDev, {
#            '-t':'development',
#            '-P':streamMain,
#        })
#        self.assertEqual(result, 0)
#
#        result = p4Run(self.repo.p4, 'streams')
#        if isinstance(result, VcsHelperErrorWrapper):
#            result.raiseError(exceptionOrExit=True)
#        self.assertEqual(len(result), 2)
#
#    def test_01_5_createClient(self):
#        VcsHelperLogger.info(f'[TEST] Create a new client for user {defaultUserName}'\
#            f' to view //{localDepotName}...')
#
#        result = self.repo.clone(clientRoot, views=[
#                f'{streamDev}/... //{clientName}/...'
#            ], stream=streamDev)
#        self.assertEqual(result, 0)
#        self.assertEqual(self.repo.client, clientName)
#        self.assertEqual(self.repo.clientRoot, clientRoot)
#        clientRoot.mkdir()
#
#    # changelist
#    def test_02_01_initCommit(self):
#        self.implTest_commit_initCommit(self.repo)
#
#    def test_02_02_writableCommit(self):
#        self.implTest_commit_writableCommit(self.repo)
#
#    def test_02_03_saveCommitSkip(self):
#        self.implTest_commit_saveCommitSkip(self.repo)
#
#    def test_02_04_directlySubmit(self):
#        self.implTest_commit_directlySubmit(self.repo)
#
#    def test_02_05_submissionFailure(self):
#        def createCommit():
#            commit = self.checkGetNewCommit(self.repo)
#            result = commit.changeFile(
#                Change(Path('b@1%2#3.txt'), ChangeType.edit))
#            self.assertEqual(result, 0)
#            # shelve
#            result = commit.save('Unused changelist')
#            self.assertEqual(result,0)
#            root = clientRoot
#            txtB = root.joinpath('b@1%2#3.txt')
#            result = p4Run(self.repo.p4, 'shelve', getP4ValidLocalPath(txtB), **{
#                '-c': commit.vcsData,
#            })
#            self.assertEqual(result, 0)
#            return commit
#        self.implTest_commit_submissionFailure(createCommit,
#                    False, ErrorCategory.remote, P4RunErrorCode.submit.value)
#
#    @unittest.skip("skip")
#    def test_02_06_clearPending(self):
#        VcsHelperLogger.info('[TEST] Clear pendings...')
#
#        # create commit
#        commit = self.checkGetNewCommit(self.repo)
#        result = commit.changeFile(
#            Change(Path('a@1%2#3.txt'), ChangeType.edit, changeContent='tmp'))
#        self.assertEqual(result, 0)
#        changes = list(commit.iterChanges())
#        self.assertEqual(len(changes), 1)
#
#        # clear pending files
#        result = self.repo.clearPendings()
#        self.assertEqual(result, 0)
#        changes = list(commit.iterChanges())
#        self.assertEqual(len(changes), 0)
#
#    @unittest.skip("skip")
#    def test_02_07_verifyCommit(self):
#        VcsHelperLogger.info('[TEST] verify commit...')
#
#        commit = self.repo.getCommit(1)
#        self.assertEqual(commit.vcsData, 1)
#
#        commit = self.repo.getCommit(99)
#        self.assertIsNone(commit)
#
#        # fetch change 
#        errorCode = (1 << 24) | (ErrorCategory.remote.value << 16) \
#                            | P4RunErrorCode.fetch_changelist.value
#        VcsHelperError.raiseType = VcsHelperError.RaiseType.exception
#        with self.assertRaises(VcsHelperException) as context:
#            commit = self.repo.getCommit(99)
#        self.assertTrue(context.exception.code, errorCode)
#        VcsHelperError.raiseType = VcsHelperError.RaiseType.return_code
#
#    @unittest.skip("skip")
#    def test_02_08_rename(self):
#        VcsHelperLogger.info('[TEST] Rename b@1%2#3.txt to b1@1%2#3.txt...')
#        commit = self.repo.getNewCommit('rename b@1%2#3.txt to b1@1%2#3.txt')
#        result = commit.changeFile(
#            Change(Path('b@1%2#3.txt'), ChangeType.move, Path('b1@1%2#3.txt'),
#                changeContent='Hello txt B@1%2#3, 2nd\nHello txt B@1%2#3'))
#        self.assertEqual(result, 0)
#        result = commit.submit()
#        self.assertEqual(result, 0)
#        self.assertEqual(commit, self.repo.getTopCommit())
#
#    @unittest.skip("skip")
#    def test_02_09_remove(self):
#        VcsHelperLogger.info('[TEST] Add x@1%2#3.txt first, then delete it...')
#        # add first
#        commit = self.repo.getNewCommit('add x@1%2#3.txt')
#        self.checkAddFile(commit, 'x@1%2#3.txt', 'Hello txt x@1%2#3')
#        result = commit.submit()
#        self.assertEqual(result, 0)
#        self.assertEqual(commit, self.repo.getTopCommit())
#        # then remove
#        commit = self.repo.getNewCommit('delete x@1%2#3.txt')
#        self.checkDeleteFile(commit, 'x@1%2#3.txt', clientRoot)
#        result = commit.submit()
#        self.assertEqual(result, 0)
#        self.assertEqual(commit, self.repo.getTopCommit())
#
#    @unittest.skip("skip")
#    def test_03_01_copyup(self):
#        VcsHelperLogger.info('[TEST] Copyup dev to main...')
#        result = self.repo.switchStream(streamMain, sync=True)
#        self.assertEqual(result, 0)
#
#        commit = self.repo.streamCopyUp(streamDev)
#        self.assertIsNotNone(commit)
#        result = commit.submit()
#        self.assertEqual(result, 0)
#
#    @unittest.skip("skip")
#    def test_03_02_mergedown(self):
#        VcsHelperLogger.info('[TEST] Merge down main to dev...')
#        commit = self.repo.getNewCommit('Add c@1%2#3.')
#        self.checkAddFile(commit, 'c@1%2#3.txt', 'Hello txt c@1%2#3')
#        result = commit.submit()
#        self.assertEqual(result, 0)
#        self.assertEqual(commit, self.repo.getTopCommit())
#
#        result = self.repo.switchStream(streamDev, sync=True)
#        self.assertEqual(result, 0)
#
#        commit = self.repo.streamMergeDown()
#        self.assertIsNotNone(commit)
#        self.assertNotEqual(commit.vcsData, -1)
#        result = self.repo.resolve(commit)
#        self.assertEqual(result, 0)
#        result = commit.submit()
#        self.assertEqual(result, 0)
#
#    @unittest.skip("skip")
#    def test_03_03_iterChangesPending(self):
#        VcsHelperLogger.info('[TEST] Iter changes, modify a.txt, rename b1.txt, add d.txt...')
#        commit = self.repo.getNewCommit('New commit, change A rename B add D.')
#
#        # change A
#        result = commit.changeFile(
#            Change(Path('a@1%2#3.txt'), ChangeType.edit,
#            changeContent='Hello txt a@1%2#3, touch 2'))
#        self.assertEqual(result, 0)
#        # rename B
#        result = commit.changeFile(
#            Change(Path('b1@1%2#3.txt'), ChangeType.move, Path('b2@1%2#3.txt'),
#                changeContent='Hello txt B@1%2#3, 3rd\nHello txt B@1%2#3, 2nd\nHello txt B@1%2#3'))
#        self.assertEqual(result, 0)
#        # add D
#        self.checkAddFile(commit, 'd@1%2#3.txt', 'Hello txt d@1%2#3')
#        # test
#        changes = list(commit.iterChanges())
#        self.assertEqual(len(changes), 3)
#        self.assertEqual(commit.lastIterResult, 0)
#        for change in changes:
#            if change.path == Path('a@1%2#3.txt'):
#                self.assertEqual(change.changeType, ChangeType.edit)
#            elif change.path == Path('d@1%2#3.txt'):
#                self.assertEqual(change.changeType, ChangeType.add)
#            elif change.path == Path('b1@1%2#3.txt'):
#                self.assertEqual(change.changeType, ChangeType.move)
#                self.assertEqual(change.destPath, Path('b2@1%2#3.txt'))
#            else:
#                self.assertTrue(False)
#        # save & test again
#        result = commit.save()
#        self.assertEqual(result, 0)
#        changes = list(commit.iterChanges())
#        self.assertEqual(len(changes), 3)
#        self.assertEqual(commit.lastIterResult, 0)
#        for change in changes:
#            if change.path == Path('a@1%2#3.txt'):
#                self.assertEqual(change.changeType, ChangeType.edit)
#            elif change.path == Path('d@1%2#3.txt'):
#                self.assertEqual(change.changeType, ChangeType.add)
#            elif change.path == Path('b1@1%2#3.txt'):
#                self.assertEqual(change.changeType, ChangeType.move)
#                self.assertEqual(change.destPath, Path('b2@1%2#3.txt'))
#            else:
#                self.assertTrue(False)
#
#        # submit
#        result = commit.submit()
#        self.assertEqual(result, 0)
#        self.assertEqual(commit, self.repo.getTopCommit())
#
#    @unittest.skip("skip")
#    def test_03_04_iterChangesSubmitted(self):
#        VcsHelperLogger.info('[TEST] Iter submitted changes...')
#
#        # empty changelist
#        commit = self.repo.getCommit(1)
#        changes = list(commit.iterChanges())
#        self.assertEqual(len(changes), 0)
#        self.assertEqual(commit.lastIterResult, 0)
#
#        # first commit
#        commit = self.repo.getCommit(3)
#        changes = list(commit.iterChanges())
#        self.assertEqual(len(changes), 1)
#        change = changes[0]
#        self.assertEqual(change.changeType,  ChangeType.add)
#        self.assertEqual(change.path, Path('a@1%2#3.txt'))
#        self.assertEqual(commit.lastIterResult, 0)
#
#        # with rename
#        commit = self.repo.getTopCommit()
#        changes = list(commit.iterChanges())
#        self.assertEqual(len(changes), 3)
#        self.assertEqual(commit.lastIterResult, 0)
#        for change in changes:
#            if change.path == Path('a@1%2#3.txt'):
#                self.assertEqual(change.changeType, ChangeType.edit)
#            elif change.path == Path('d@1%2#3.txt'):
#                self.assertEqual(change.changeType, ChangeType.add)
#            elif change.path == Path('b1@1%2#3.txt'):
#                self.assertEqual(change.changeType, ChangeType.move)
#                self.assertEqual(change.destPath, Path('b2@1%2#3.txt'))
#            else:
#                self.assertTrue(False)
#
#        # other stream
#        commit = self.repo.getCommit(10)
#        changes = list(commit.iterChanges())
#        self.assertEqual(len(changes), 0)
#        errorCode = (ErrorCategory.commit.value << 16) | CommitErrorCode.wrong_depot.value
#        self.assertEqual(commit.lastIterResult, errorCode)
#
#    # tag
#    @unittest.skip("skip")
#    def test_04_01_tag(self):
#        VcsHelperLogger.info('[TEST] tag (p4 label)...')
#
#        labelName = 'test_tag'
#        labelMessage = 'Test tag\n'
#        # inexistent tag
#        commit = self.repo.getCommitFromTag(labelName)
#        self.assertIsNone(commit)
#
#        # add tag
#        result = self.repo.setTag(labelName, self.repo.getCommit(3), labelMessage)
#        self.assertEqual(result, 0)
#        commit = self.repo.getCommitFromTag(labelName)
#        self.assertEqual(commit.vcsData, 3)
#        msg = self.repo.getTagMessage(labelName)
#        self.assertEqual(msg, labelMessage)
#
#        # update commit
#        result = self.repo.setTag(labelName, self.repo.getCommit(10), labelMessage)
#        self.assertEqual(result, 0)
#        commit = self.repo.getCommitFromTag(labelName)
#        self.assertEqual(commit.vcsData, 10)
#        msg = self.repo.getTagMessage(labelName)
#        self.assertEqual(msg, labelMessage)
#
#        # update message
#        labelMessage2 = 'Test tag2\n'
#        commit = self.repo.getCommitFromTag(labelName)
#        self.assertEqual(commit.vcsData, 10)
#        result = self.repo.setTag(labelName, commit, labelMessage2)
#        self.assertEqual(result, 0)
#        commit = self.repo.getCommitFromTag(labelName)
#        self.assertEqual(commit.vcsData, 10)
#        msg = self.repo.getTagMessage(labelName)
#        self.assertEqual(msg, labelMessage2)
#
#        # delete tag
#        result = self.repo.deleteTag(labelName)
#        self.assertEqual(result, 0)
#        commit = self.repo.getCommitFromTag(labelName)
#        self.assertIsNone(commit)
#
#    # sync
#    @unittest.skip("skip")
#    def test_05_01_sync(self):
#        VcsHelperLogger.info('[TEST] sync...')
#
#        root = clientRoot
#        txtA  = root.joinpath('a@1%2#3.txt')
#        txtB  = root.joinpath('b@1%2#3.txt')
#        txtB1 = root.joinpath('b1@1%2#3.txt')
#        txtB2 = root.joinpath('b2@1%2#3.txt')
#        txtC  = root.joinpath('c@1%2#3.txt')
#        txtD  = root.joinpath('d@1%2#3.txt')
#
#        # sync to init
#        result = self.repo.sync(self.repo.getCommit(3))
#        self.assertEqual(result, 0)
#        self.assertTrue(txtA.exists())
#        self.assertFalse(txtB.exists())
#        self.assertFalse(txtB1.exists())
#        self.assertFalse(txtB2.exists())
#        self.assertFalse(txtC.exists())
#        self.assertFalse(txtD.exists())
#        text = txtA.read_text()
#        self.assertEqual(text, 'Hello txt a@1%2#3')
#
#        # sync to latest
#        result = self.repo.sync()
#        self.assertEqual(result, 0)
#        self.assertTrue(txtA.exists())
#        self.assertFalse(txtB.exists())
#        self.assertFalse(txtB1.exists())
#        self.assertTrue(txtB2.exists())
#        self.assertTrue(txtC.exists())
#        self.assertTrue(txtD.exists())
#        text = txtA.read_text()
#        self.assertEqual(text,
#            'Hello txt a@1%2#3, touch 2')
#        text = txtB2.read_text()
#        self.assertEqual(text,
#            'Hello txt B@1%2#3, 3rd\nHello txt B@1%2#3, 2nd\nHello txt B@1%2#3')
#
#    @unittest.skip("skip")
#    def test_05_02_sync_reset(self):
#        VcsHelperLogger.info('[TEST] sync with reset...')
#
#        root = clientRoot
#        txtA = root.joinpath('a@1%2#3.txt')
#        txtE = root.joinpath('3@1%2#3.txt')
#
#        commit = self.repo.getNewCommit('tmp')
#        result = commit.changeFile(
#            Change(txtA.relative_to(root), ChangeType.edit,
#            changeContent='Hello txt a@1%2#3, touch 3'))
#        self.assertEqual(result, 0)
#
#        result = commit.changeFile(
#            Change(txtE.relative_to(root), ChangeType.add,
#            changeContent='Hello txt e@1%2#3'))
#        self.assertEqual(result, 0)
#
#        # sync to init
#        result = self.repo.sync(self.repo.getCommit(3), reset=True)
#        self.assertEqual(result, 0)
#        self.assertTrue(txtA.exists())
#        self.assertFalse(txtE.exists())
#        text = txtA.read_text()
#        self.assertEqual(text, 'Hello txt a@1%2#3')
#
#        # sync to latest
#        result = self.repo.sync(reset=True)
#        self.assertEqual(result, 0)
#        self.assertTrue(txtA.exists())
#        self.assertFalse(txtE.exists())
#        text = txtA.read_text()
#        self.assertEqual(text,
#            'Hello txt a@1%2#3, touch 2')
#
#    # changelist
#    @unittest.skip("skip")
#    def test_05_03_iterChangesUnresolved(self):
#        VcsHelperLogger.info('[TEST] iter unresolved changes...')
#
#        root = clientRoot
#        txtA = root.joinpath('a@1%2#3.txt')
#        txtE = root.joinpath('e@1%2#3.txt')
#
#        # writable check
#        commit = self.repo.getCommit(3)
#        changes = list(commit.iterConflictedChanges())
#        self.assertEqual(len(changes), 0)
#        errorCode = (ErrorCategory.commit.value << 16) | CommitErrorCode.writable.value
#        self.assertEqual(commit.lastIterResult, errorCode)
#
#        # no unresolved
#            # create new pending changelist
#        commit = self.repo.getNewCommit('tmp')
#        result = commit.changeFile(
#            Change(Path('a@1%2#3.txt'), ChangeType.edit,
#            changeContent='Hello txt a@1%2#3, touch 3'))
#        self.assertEqual(result, 0)
#
#        result = commit.changeFile(
#            Change(Path('e@1%2#3.txt'), ChangeType.add,
#            changeContent='Hello txt e@1%2#3'))
#        self.assertEqual(result, 0)
#
#            # test
#        changes = list(commit.iterConflictedChanges())
#        self.assertEqual(len(changes), 0)
#        self.assertEqual(commit.lastIterResult, 0)
#
#        # need resolve
#            # clear pendings
#        result = self.repo.clearPendings()
#        self.assertEqual(result, 0)
#        self.assertFalse(txtE.exists())
#            # create conflict 
#        fileSpec = getP4ValidLocalPath(txtA)
#        fileSpec1 = fileSpec + '#1'
#        result = p4Run(self.repo.p4, 'sync', fileSpec1)
#        self.assertNotIsInstance(result, VcsHelperErrorWrapper)
#
#        result = commit.changeFile(
#            Change(Path('a@1%2#3.txt'), ChangeType.edit,
#            changeContent='Hello txt a@1%2#3, touch 3'))
#        self.assertEqual(result, 0)
#
#        result = p4Run(self.repo.p4, 'sync', fileSpec)
#        self.assertNotIsInstance(result, VcsHelperErrorWrapper)
#
#        # test
#        changes = list(commit.iterConflictedChanges())
#        self.assertEqual(len(changes), 1)
#        self.assertEqual(commit.lastIterResult, 0)
#            # reset to latest
#        result = self.repo.sync(reset=True)
#        self.assertEqual(result, 0)
#        self.assertFalse(txtE.exists())
#
#    @unittest.skip("skip")
#    def test_05_04_iterCommits(self):
#        VcsHelperLogger.info('[TEST] iter commits...')
#        
#        commits = list(self.repo.iterCommits())
#        self.assertEqual(self.repo.lastIterResult, 0)
#        self.assertEqual(len(commits), 8)
#        clList = [3,4,5,7,8,9,12,13]
#        for index, commit in enumerate(commits):
#            self.assertFalse(commit.isWritable)
#            self.assertEqual(commit.vcsData, clList[index])
#
#        commits = list(self.repo.iterCommits(after=self.repo.getCommit(5)))
#        self.assertEqual(self.repo.lastIterResult, 0)
#        self.assertEqual(len(commits), 5)
#        clList = [7,8,9,12,13]
#        for index, commit in enumerate(commits):
#            self.assertFalse(commit.isWritable)
#            self.assertEqual(commit.vcsData, clList[index])
#
#        commits = list(self.repo.iterCommits(after=self.repo.getCommit(13)))
#        self.assertEqual(self.repo.lastIterResult, 0)
#        self.assertEqual(len(commits), 0)
#
#    def assertDiffs(self, changes, expectedDict):
#        changes = list(changes)
#        #for change in changes:
#        #    print(change)
#        for change in changes:
#            self.assertEqual(self.repo.lastIterResult, 0)
#            self.assertIn(change.path, expectedDict)
#            expectedChanges = expectedDict[change.path]
#            expected = expectedChanges[0]
#            self.assertEqual(change.path, expected.path)
#            self.assertEqual(change.changeType, expected.changeType)
#            self.assertEqual(change.destPath, expected.destPath)
#            del expectedChanges[0]
#
#    @unittest.skip("skip")
#    def test_06_01_iterDiffs_DifferentSupport(self):
#        VcsHelperLogger.info('[TEST] iter diffs...')
#
#        # prepare
#        commit5 = self.repo.getCommit(5)
#        commit13 = self.repo.getCommit(13)
#        newCommit1 = self.repo.getNewCommit('tmp1')
#        newCommit2 = self.repo.getNewCommit('tmp2')
#        # newCommit1
#        result = newCommit1.changeFile(
#            Change(Path('a@1%2#3.txt'), ChangeType.edit,
#                changeContent='Hello txt b@1%2#3, 3rd'))
#        self.assertEqual(result, 0)
#        result = newCommit1.changeFile(
#            Change(Path('c@1%2#3.txt'), ChangeType.move, Path('e@1%2#3.txt'),
#                changeContent='Hello txt E@1%2#3\nHello txt C@1%2#3'))
#        self.assertEqual(result, 0)
#        result = newCommit1.save()
#        self.assertEqual(result, 0)
#        # newCommit2
#        result = newCommit2.changeFile(
#            Change(Path('b2@1%2#3.txt'), ChangeType.delete))
#        self.assertEqual(result, 0)
#        result = newCommit2.save()
#        self.assertEqual(result, 0)
#        # diff from #5 to #13
#        expectedDict = {
#            Path('a@1%2#3.txt'): [Change(Path('a@1%2#3.txt'), ChangeType.edit)],
#            Path('b@1%2#3.txt'): [Change(Path('b@1%2#3.txt'), ChangeType.move,
#                                        Path('b2@1%2#3.txt'))],
#            Path('c@1%2#3.txt'): [Change(Path('c@1%2#3.txt'), ChangeType.add)],
#            Path('d@1%2#3.txt'): [Change(Path('d@1%2#3.txt'), ChangeType.add)],
#        }
#        self.assertDiffs(commit13.iterDiffs(commit5), expectedDict)
#        
#        # diff from #13 to #5
#        expectedDict = {
#            Path('a@1%2#3.txt'): [Change(Path('a@1%2#3.txt'), ChangeType.edit)],
#            Path('b2@1%2#3.txt'): [Change(Path('b2@1%2#3.txt'), ChangeType.move,
#                                        Path('b@1%2#3.txt'))],
#            Path('c@1%2#3.txt'): [Change(Path('c@1%2#3.txt'), ChangeType.delete)],
#            Path('d@1%2#3.txt'): [Change(Path('d@1%2#3.txt'), ChangeType.delete)],
#        }
#        self.assertDiffs(commit5.iterDiffs(commit13), expectedDict)
#
#        # diff from #5 to newCommit1
#        expectedDict = {
#            Path('a@1%2#3.txt'): [Change(Path('a@1%2#3.txt'), ChangeType.edit)],
#            Path('b@1%2#3.txt'): [Change(Path('b@1%2#3.txt'), ChangeType.move,
#                                        Path('b2@1%2#3.txt'))],
#            Path('e@1%2#3.txt'): [Change(Path('e@1%2#3.txt'), ChangeType.add)],
#            Path('d@1%2#3.txt'): [Change(Path('d@1%2#3.txt'), ChangeType.add)],
#        }
#        self.assertDiffs(newCommit1.iterDiffs(commit5), expectedDict)
#
#        # diff from newCommit1 to newCommit2
#        expectedDict = {
#            Path('a@1%2#3.txt'): [Change(Path('a@1%2#3.txt'), ChangeType.edit)],
#            Path('e@1%2#3.txt'): [Change(Path('e@1%2#3.txt'), ChangeType.move,
#                                        Path('c@1%2#3.txt'))],
#            Path('b2@1%2#3.txt'): [Change(Path('b2@1%2#3.txt'), ChangeType.delete)],
#        }
#        self.assertDiffs(newCommit2.iterDiffs(newCommit1), expectedDict)
#        
#        # clear pendings
#        result = self.repo.clearPendings()
#        self.assertEqual(result, 0)
#
#    @unittest.skip("skip")
#    def test_06_02_iterDiffs_FullTest(self):
#        VcsHelperLogger.info('[TEST] iter diffs, full test, preparation...')
#
#        validNextOpDict = {
#            'add': ('edit', 'delete', 'move'),
#            'edit': ('edit', 'delete', 'move'),
#            'delete': ('add', 'move_dest'),
#            'move': ('add', 'move_dest'),
#            'move_dest': ('edit', 'delete', 'move'),
#        }
#        opChains = []
#        chainLength = 5
#        moveTmpFiles = []
#        moveDestTmpFiles = []
#        def iterChains(op, chain):
#            if len(chain) > 1:
#                yield chain
#            if len(chain) < chainLength:
#                for nextOp in validNextOpDict[op]:
#                    yield from iterChains(nextOp, (*chain, nextOp))
#
#        for op in validNextOpDict.keys():
#            for chain in iterChains(op, (op,)):
#                for opi in chain:
#                    if op == 'move_dest':
#                        index = len(moveTmpFiles)
#                        moveTmpFiles.append(f'move_tmp{index}')
#                opChains.append((*chain, '-'.join(chain)))
#
#        def handleOp(commit, op, name):
#            if op == 'add':
#                self.checkAddFile(commit, name, f'Add {name}',
#                                  localRoot=clientRoot, parent=commitRoot)
#            elif op == 'edit':
#                result = commit.changeFile(Change(commitRoot.joinpath(name),
#                            ChangeType.edit, changeContent=f'Edit {name}'))
#                self.assertEqual(result, 0)
#            elif op == 'delete':
#                self.checkDeleteFile(commit, name, clientRoot, parent=commitRoot)
#            elif op == 'move':
#                index = len(moveDestTmpFiles)
#                destName = f'move_dest_tmp{index}'
#                moveDestTmpFiles.append(destName)
#                result = commit.changeFile(Change(commitRoot.joinpath(name),
#                            ChangeType.move, commitRoot.joinpath(destName),
#                            changeContent=f'Move from {name} to {destName}'))
#                self.assertEqual(result, 0)
#            elif op == 'move_dest':
#                srcName = moveTmpFiles.pop()
#                result = commit.changeFile(Change(commitRoot.joinpath(srcName),
#                            ChangeType.move, commitRoot.joinpath(name),
#                            changeContent=f'Move from {srcName} to {name}'))
#                self.assertEqual(result, 0)
#
#        commits = []
#        commitRoot = Path('diff_full_test')
#        # init commit
#        commits.append(self.repo.getNewCommit('Init commit for diff full test.'))
#            # add init files
#        for opChain in opChains:
#            name = opChain[-1]
#            opChain = opChain[:-1]
#            if opChain[0] in ['edit', 'delete', 'move']:
#                self.checkAddFile(commits[0], name, f'Init {name}\n',
#                                        localRoot=clientRoot, parent=commitRoot)
#            # add a temp move src
#        for moveTmpFile in moveTmpFiles:
#            self.checkAddFile(commits[0], moveTmpFile, f'Init {moveTmpFile}\n',
#                                        localRoot=clientRoot, parent=commitRoot)
#            #commit
#        self.assertSaveSubmit(self.repo, commits[0])
#
#        # loop to commit all changes
#        for repeatIndex in range(chainLength):
#            commitIndex = repeatIndex + 1
#            commit = self.repo.getNewCommit(
#                f'Diff full test round {commitIndex}.')
#            commits.append(commit)
#            for opChain in opChains:
#                if commitIndex >= len(opChain):
#                    continue
#                name = opChain[-1]
#                op = opChain[repeatIndex]
#                handleOp(commit, op, name)
#            self.assertSaveSubmit(self.repo, commit)
#
#        # test
#        VcsHelperLogger.info('[TEST] iter diffs, full test...')
#
#        opResultDict = {
#            frozenset(('add', 'edit')): 'add',
#            frozenset(('add', 'delete')): 'none',
#            frozenset(('add', 'move')): 'none',
#
#            frozenset(('edit', 'edit')): 'edit',
#            frozenset(('edit', 'delete')): 'delete',
#            frozenset(('edit', 'move')): 'move',
#
#            frozenset(('delete', 'add')): 'edit',
#            frozenset(('delete', 'move_dest')): 'edit',
#
#            frozenset(('move', 'add')): 'edit',
#            frozenset(('move', 'move_dest')): 'edit',
#
#            frozenset(('move_dest', 'edit')): 'move_dest',
#            frozenset(('move_dest', 'delete')): 'none',
#            frozenset(('move_dest', 'move')): 'none',
#        }
#        def getExpectedChangeType(opChain: typing.Iterable) -> str:
#            
#            result = 1
#
#        expectedResults = {}
#        for firstCommitIndex in range(1, len(commits)):
#            for secondCommitIndex in range(0, firstCommitIndex):
#                expectedResult = expectedResults.setdefault(
#                    frozenset((firstCommitIndex, secondCommitIndex)), {})
#                
#
#        #for opChain in opChains:
#        #    print(opChain[-1])
#        
#
#
#        #for opChain in opChains:
#        #    print(opChain[-1])

        # always put at the last test
        # hold the test, to keep the test p4 server and repo
        input("End of the test; you can check p4 repo at 127.0.0.1:1666. Press Enter to continue...")

# TODO: P4 iter changes
# TODO: partial copyup / mergedown
# TODO: undo copyup / mergedown? in repo-sync?