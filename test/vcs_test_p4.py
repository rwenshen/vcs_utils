from pathlib import Path

from ..p4.p4_repo import P4RepoErrorCode

from .vcs_test_base import VCSTestBase
from ..common.logger import *
from ..common.change import ChangeType, Change
from ..common.commit import CommitErrorCode
from ..p4 import *
from ..p4.p4_runner import *
from ..p4.p4_runner import P4RunErrorCode
from ..p4.p4_server import P4Server


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
        cls.server = None
        cls.repo = None

    @classmethod
    def tearDownClass(cls):
        if cls.server is not None:
            del cls.server
        if cls.repo is not None:
            del cls.repo
        super(P4RepoTest, cls).tearDownClass()

    def setUp(self):
        pass
        

    def tearDown(self):
        pass
        
    @property
    def server(self):
        return self.__class__.server

    @property
    def repo(self):
        return self.__class__.repo

    # common functions
    def checkAddFile(self, commit, fileName: str, content: str) -> Path:
        root = clientRoot
        txtFile = root.joinpath(fileName)
        result = commit.changeFile(
            Change(txtFile.relative_to(root), ChangeType.add,
                changeContent = content
            ))
        self.assertEqual(result, 0)
        return txtFile

    def checkDeleteFile(self, commit, fileName: str) -> Path:
        root = clientRoot
        txtFile = root.joinpath(fileName)
        self.assertTrue(txtFile.exists())
        result = commit.changeFile(
            Change(txtFile.relative_to(root), ChangeType.delete))
        self.assertEqual(result, 0)
        self.assertFalse(txtFile.exists())
        return txtFile

    # create server and repo
    def test_01_1_createServer(self):
        VcsHelperLogger.info(f'Create P4 server at {str(p4LocalServerRoot)}')
        self.__class__.server = P4Server(p4LocalServerRoot, user=defaultUserName)

    def test_01_2_repoCreate(self):
        VcsHelperLogger.info('\nCreate repo...')
        self.__class__.repo = P4Repo(
                p4Port=self.server.p4.port,
                p4Client=clientName,
                p4User=defaultUserName)
        VcsHelperLogger.info(f'P4Repo {self.repo.description} has been created.')

        # no client check
        errorCode = (1 << 24) | (ErrorCategory.repo.value << 16) \
                            | P4RepoErrorCode.client_invalid.value
        with self.assertRaises(VcsHelperException) as context:
            self.repo.getTopCommit()
        self.assertTrue(context.exception.code, errorCode)

    def test_01_3_createDepot(self):
        VcsHelperLogger.info(f'\nCreate a new local depot //{localDepotName}/...')
        result = self.repo.updateSpec('depot', localDepotName, {'-t':'local'})
        self.assertEqual(result, 0)

        VcsHelperLogger.info(f'\nCreate a new stream depot //{streamDepotName}/...')
        result = self.repo.updateSpec('depot', streamDepotName, {'-t':'stream'})
        self.assertEqual(result, 0)

        result = p4Run(self.repo.p4, 'depots')
        if isinstance(result, VcsHelperErrorWrapper):
            result.raiseError(exceptionOrExit=True)
        self.assertEqual(len(result), 3)

    def test_01_4_createStream(self):
        VcsHelperLogger.info(f'\nCreate stream {streamMain}')
        result = self.repo.updateSpec('stream', streamMain, {'-t':'mainline'})
        self.assertEqual(result, 0)

        VcsHelperLogger.info(f'\nCreate stream {streamDev}')
        result = self.repo.updateSpec('stream', streamDev, {
            '-t':'development',
            '-P':streamMain,
        })
        self.assertEqual(result, 0)

        result = p4Run(self.repo.p4, 'streams')
        if isinstance(result, VcsHelperErrorWrapper):
            result.raiseError(exceptionOrExit=True)
        self.assertEqual(len(result), 2)

    def test_01_5_createClient(self):
        VcsHelperLogger.info(f'\nCreate a new client for user {defaultUserName}'\
            f' to view //{localDepotName}...')

        result = self.repo.clone(clientRoot, views=[
                f'{streamDev}/... //{clientName}/...'
            ], stream=streamDev)
        self.assertEqual(result, 0)
        self.assertEqual(self.repo.client, clientName)
        self.assertEqual(self.repo.clientRoot, clientRoot)
        clientRoot.mkdir()

    # changelist
    def test_02_01_newChangelist(self):
        VcsHelperLogger.info('\nAdd a@1%2#3.txt...')
        commit = self.repo.getNewCommit('Init commit.')
        self.checkAddFile(commit, 'a@1%2#3.txt', 'Hello txt a@1%2#3')
        result = commit.save()
        self.assertEqual(result, 0)
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, self.repo.getTopCommit())

    def test_02_02_writableCommit(self):
        VcsHelperLogger.info('\nAssert writable commit...')
        commit = self.repo.getTopCommit()
        root = clientRoot
        txtA = root.joinpath('a@1%2#3.txt')
        result = commit.changeFile(
            Change(txtA.relative_to(root), ChangeType.edit))
        errorCode = (ErrorCategory.commit.value << 16) | CommitErrorCode.writable.value
        self.assertEqual(result, errorCode)

    def test_02_03_saveCommitSkip(self):
        VcsHelperLogger.info('\nSkip commit save, add b.txt...')
        commit = self.repo.getNewCommit('The 2nd commit.')
        result = commit.save()
        self.assertNotEqual(result, 0)
        self.checkAddFile(commit, 'b@1%2#3.txt', 'Hello txt b@1%2#3')
        result = commit.save()
        self.assertEqual(result, 0)
        result = commit.save()
        self.assertNotEqual(result,0)
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, self.repo.getTopCommit())

    def test_02_04_directlySubmit(self):
        VcsHelperLogger.info('\nSubmit directly, edit b@1%2#3.txt...')
        commit = self.repo.getNewCommit('Edit b@1%2#3.txt')
        root = clientRoot
        txtB = root.joinpath('b@1%2#3.txt')
        result = commit.changeFile(
            Change(txtB.relative_to(root), ChangeType.edit,
                changeContent='Hello txt b@1%2#3, 2nd'
            ))
        self.assertEqual(result, 0)
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, self.repo.getTopCommit())

    def test_02_05_submissionFailure(self):
        VcsHelperLogger.info('\nSubmission Failure...')
        commit = self.repo.getNewCommit('Unused changelist')
        root = clientRoot
        txtB = root.joinpath('b@1%2#3.txt')
        result = commit.changeFile(
            Change(txtB.relative_to(root), ChangeType.edit))
        self.assertEqual(result, 0)
        
        # shelve
        result = commit.save()
        self.assertEqual(result,0)
        result = p4Run(self.repo.p4, 'shelve', getP4ValidLocalPath(txtB), **{
            '-c': commit.vcsData,
        })
        self.assertEqual(result, 0)

        errorCode = (1 << 24) | (ErrorCategory.remote.value << 16) \
                            | P4RunErrorCode.submit.value
        # submission failure with exception
        VcsHelperError.raiseType = VcsHelperError.RaiseType.exception
        with self.assertRaises(VcsHelperException) as context:
            commit.submit()
        self.assertTrue(context.exception.code, errorCode)

        # submission failure with return code
        VcsHelperError.raiseType = VcsHelperError.RaiseType.return_code
        result = commit.submit()
        self.assertEqual(result, errorCode)

    def test_02_06_clearPending(self):
        VcsHelperLogger.info('\nClear pendings...')

        commit = self.repo.getNewCommit('default changelist')
        root = clientRoot
        txtB = root.joinpath('a@1%2#3.txt')
        result = commit.changeFile(
            Change(txtB.relative_to(root), ChangeType.edit))
        self.assertEqual(result, 0)

        result = p4Run(self.repo.p4, 'changes', **{
            '-s': 'pending'
        })
        self.assertNotIsInstance(result, VcsHelperErrorWrapper)
        self.assertEqual(len(result), 1)
        commit = self.repo.getNewCommit('default changelist')
        self.assertIn('Files', commit.commitRef)
        self.assertEqual(len(commit.commitRef['Files']), 1)

        result = self.repo.clearPendings()
        self.assertEqual(result, 0)
        result = p4Run(self.repo.p4, 'changes', **{
            '-s': 'pending'
        })
        self.assertNotIsInstance(result, VcsHelperErrorWrapper)
        self.assertEqual(len(result), 0)
        commit = self.repo.getNewCommit('default changelist')
        self.assertNotIn('Files', commit.commitRef)

    def test_02_08_verifyCommit(self):
        commit = self.repo.getCommit(1)
        self.assertEqual(commit.vcsData, 1)

        commit = self.repo.getCommit(99)
        self.assertIsNone(commit)

        # fetch change 
        errorCode = (1 << 24) | (ErrorCategory.remote.value << 16) \
                            | P4RunErrorCode.fetch_changelist.value
        VcsHelperError.raiseType = VcsHelperError.RaiseType.exception
        with self.assertRaises(VcsHelperException) as context:
            commit = self.repo.getCommit(99)
        self.assertTrue(context.exception.code, errorCode)
        VcsHelperError.raiseType = VcsHelperError.RaiseType.return_code

    def test_02_09_rename(self):
        VcsHelperLogger.info('\nRename b@1%2#3.txt to b1@1%2#3.txt...')
        commit = self.repo.getNewCommit('rename b@1%2#3.txt to b1@1%2#3.txt')
        root = clientRoot
        txtB = root.joinpath('b@1%2#3.txt')
        txtB1 = root.joinpath('b1@1%2#3.txt')
        result = commit.changeFile(
            Change(txtB.relative_to(root), ChangeType.move,
                txtB1.relative_to(root),
                changeContent='Hello txt B@1%2#3, 2nd\nHello txt B@1%2#3'))
        self.assertEqual(result, 0)
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, self.repo.getTopCommit())

    def test_02_10_remove(self):
        VcsHelperLogger.info('\nAdd x@1%2#3.txt first, then delete it...')
        # add first
        commit = self.repo.getNewCommit('add x@1%2#3.txt')
        self.checkAddFile(commit, 'x@1%2#3.txt', 'Hello txt x@1%2#3')
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, self.repo.getTopCommit())
        # then remove
        commit = self.repo.getNewCommit('delete x@1%2#3.txt')
        self.checkDeleteFile(commit, 'x@1%2#3.txt')
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, self.repo.getTopCommit())

    def test_03_01_copyup(self):
        VcsHelperLogger.info('\nCopyup dev to main...')
        result = self.repo.switchStream(streamMain, sync=True)
        self.assertEqual(result, 0)

        commit = self.repo.streamCopyUp(streamDev)
        self.assertIsNotNone(commit)
        result = commit.submit()
        self.assertEqual(result, 0)

    def test_03_02_mergedown(self):
        VcsHelperLogger.info('\nMerge down main to dev...')
        commit = self.repo.getNewCommit('Add c@1%2#3.')
        self.checkAddFile(commit, 'c@1%2#3.txt', 'Hello txt c@1%2#3')
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, self.repo.getTopCommit())

        result = self.repo.switchStream(streamDev, sync=True)
        self.assertEqual(result, 0)

        commit = self.repo.streamMergeDown()
        self.assertIsNotNone(commit)
        commit.save()
        self.assertEqual(result, 0)
        result = self.repo.resolve(commit)
        self.assertEqual(result, 0)
        result = commit.submit()
        self.assertEqual(result, 0)

    def test_03_03_iterChangesPending(self):
        VcsHelperLogger.info('\nIter changes, modify a.txt, rename b1.txt, add d.txt...')
        commit = self.repo.getNewCommit('New commit, change A rename B add D.')
        root = clientRoot
        
        # change A
        txtA = root.joinpath('a@1%2#3.txt')
        result = commit.changeFile(
            Change(txtA.relative_to(root), ChangeType.edit,
            changeContent='Hello txt a@1%2#3, touch 2'))
        self.assertEqual(result, 0)
        # rename B
        txtB1 = root.joinpath('b1@1%2#3.txt')
        txtB2 = root.joinpath('b2@1%2#3.txt')
        result = commit.changeFile(
            Change(txtB1.relative_to(root), ChangeType.move,
                txtB2.relative_to(root),
                changeContent='Hello txt B@1%2#3, 3rd\nHello txt B@1%2#3, 2nd\nHello txt B@1%2#3'))
        self.assertEqual(result, 0)
        # add D
        txtD = self.checkAddFile(commit, 'd@1%2#3.txt', 'Hello txt d@1%2#3')
        # test
        changes = list(commit.iterChanges())
        self.assertEqual(len(changes), 3)
        self.assertEqual(commit.lastIterResult, 0)
        for change in changes:
            if change.path == txtA.relative_to(root):
                self.assertEqual(change.changeType, ChangeType.edit)
            elif change.path == txtD.relative_to(root):
                self.assertEqual(change.changeType, ChangeType.add)
            elif change.path == txtB1.relative_to(root):
                self.assertEqual(change.changeType, ChangeType.move)
                self.assertEqual(change.destPath, txtB2.relative_to(root))
            else:
                self.assertTrue(False)
        # save & test again
        result = commit.save()
        self.assertEqual(result, 0)
        changes = list(commit.iterChanges())
        self.assertEqual(len(changes), 3)
        self.assertEqual(commit.lastIterResult, 0)
        for change in changes:
            if change.path == txtA.relative_to(root):
                self.assertEqual(change.changeType, ChangeType.edit)
            elif change.path == txtD.relative_to(root):
                self.assertEqual(change.changeType, ChangeType.add)
            elif change.path == txtB1.relative_to(root):
                self.assertEqual(change.changeType, ChangeType.move)
                self.assertEqual(change.destPath, txtB2.relative_to(root))
            else:
                self.assertTrue(False)

        # submit
        result = commit.submit()
        self.assertEqual(result, 0)
        self.assertEqual(commit, self.repo.getTopCommit())

    def test_03_04_iterChangesSubmitted(self):
        root = clientRoot
        txtA = root.joinpath('a@1%2#3.txt')
        txtB1 = root.joinpath('b1@1%2#3.txt')
        txtB2 = root.joinpath('b2@1%2#3.txt')
        txtD = root.joinpath('d@1%2#3.txt')
        
        # empty changelist
        commit = self.repo.getCommit(1)
        changes = list(commit.iterChanges())
        self.assertEqual(len(changes), 0)
        self.assertEqual(commit.lastIterResult, 0)

        # first commit
        commit = self.repo.getCommit(3)
        changes = list(commit.iterChanges())
        self.assertEqual(len(changes), 1)
        change = changes[0]
        self.assertEqual(change.changeType,  ChangeType.add)
        self.assertEqual(change.path, txtA.relative_to(root))
        self.assertEqual(commit.lastIterResult, 0)

        # with rename
        commit = self.repo.getTopCommit()
        changes = list(commit.iterChanges())
        self.assertEqual(len(changes), 3)
        self.assertEqual(commit.lastIterResult, 0)
        for change in changes:
            if change.path == txtA.relative_to(root):
                self.assertEqual(change.changeType, ChangeType.edit)
            elif change.path == txtD.relative_to(root):
                self.assertEqual(change.changeType, ChangeType.add)
            elif change.path == txtB1.relative_to(root):
                self.assertEqual(change.changeType, ChangeType.move)
                self.assertEqual(change.destPath, txtB2.relative_to(root))
            else:
                self.assertTrue(False)

        # other stream
        commit = self.repo.getCommit(10)
        changes = list(commit.iterChanges())
        self.assertEqual(len(changes), 0)
        errorCode = (ErrorCategory.commit.value << 16) | CommitErrorCode.wrongDepot.value
        self.assertEqual(commit.lastIterResult, errorCode)

    # tag
    def test_04_01_tag(self):
        labelName = 'test_tag'
        labelMessage = 'Test tag\n'
        # inexistent tag
        commit = self.repo.getCommitFromTag(labelName)
        self.assertIsNone(commit)

        # add tag
        result = self.repo.setTag(labelName, self.repo.getCommit(3), labelMessage)
        self.assertEqual(result, 0)
        commit = self.repo.getCommitFromTag(labelName)
        self.assertEqual(commit.vcsData, 3)
        msg = self.repo.getTagMessage(labelName)
        self.assertEqual(msg, labelMessage)

        # update commit
        result = self.repo.setTag(labelName, self.repo.getCommit(10), labelMessage)
        self.assertEqual(result, 0)
        commit = self.repo.getCommitFromTag(labelName)
        self.assertEqual(commit.vcsData, 10)
        msg = self.repo.getTagMessage(labelName)
        self.assertEqual(msg, labelMessage)

        # update message
        labelMessage2 = 'Test tag2\n'
        commit = self.repo.getCommitFromTag(labelName)
        self.assertEqual(commit.vcsData, 10)
        result = self.repo.setTag(labelName, commit, labelMessage2)
        self.assertEqual(result, 0)
        commit = self.repo.getCommitFromTag(labelName)
        self.assertEqual(commit.vcsData, 10)
        msg = self.repo.getTagMessage(labelName)
        self.assertEqual(msg, labelMessage2)

        # delete tag
        result = self.repo.deleteTag(labelName)
        self.assertEqual(result, 0)
        commit = self.repo.getCommitFromTag(labelName)
        self.assertIsNone(commit)

    # sync
    def test_05_01_sync(self):
        root = clientRoot
        txtA = root.joinpath('a@1%2#3.txt')
        txtB = root.joinpath('b@1%2#3.txt')
        txtB1 = root.joinpath('b1@1%2#3.txt')
        txtB2 = root.joinpath('b2@1%2#3.txt')
        txtC = root.joinpath('c@1%2#3.txt')
        txtD = root.joinpath('d@1%2#3.txt')

        # sync to init
        result = self.repo.sync(self.repo.getCommit(3))
        self.assertEqual(result, 0)
        self.assertTrue(txtA.exists())
        self.assertFalse(txtB.exists())
        self.assertFalse(txtB1.exists())
        self.assertFalse(txtB2.exists())
        self.assertFalse(txtC.exists())
        self.assertFalse(txtD.exists())
        text = txtA.read_text()
        self.assertEqual(text, 'Hello txt a@1%2#3')

        # sync to latest
        result = self.repo.sync()
        self.assertEqual(result, 0)
        self.assertTrue(txtA.exists())
        self.assertFalse(txtB.exists())
        self.assertFalse(txtB1.exists())
        self.assertTrue(txtB2.exists())
        self.assertTrue(txtC.exists())
        self.assertTrue(txtD.exists())
        text = txtA.read_text()
        self.assertEqual(text,
            'Hello txt a@1%2#3, touch 2')
        text = txtB2.read_text()
        self.assertEqual(text,
            'Hello txt B@1%2#3, 3rd\nHello txt B@1%2#3, 2nd\nHello txt B@1%2#3')

    def test_05_02_sync_reset(self):
        root = clientRoot
        txtA = root.joinpath('a@1%2#3.txt')
        txtE = root.joinpath('3@1%2#3.txt')

        commit = self.repo.getNewCommit('tmp')
        result = commit.changeFile(
            Change(txtA.relative_to(root), ChangeType.edit,
            changeContent='Hello txt a@1%2#3, touch 3'))
        self.assertEqual(result, 0)

        result = commit.changeFile(
            Change(txtE.relative_to(root), ChangeType.add,
            changeContent='Hello txt e@1%2#3'))
        self.assertEqual(result, 0)

        # sync to init
        result = self.repo.sync(self.repo.getCommit(3), reset=True)
        self.assertEqual(result, 0)
        self.assertTrue(txtA.exists())
        self.assertFalse(txtE.exists())
        text = txtA.read_text()
        self.assertEqual(text, 'Hello txt a@1%2#3')

        # sync to latest
        result = self.repo.sync(reset=True)
        self.assertEqual(result, 0)
        self.assertTrue(txtA.exists())
        self.assertFalse(txtE.exists())
        text = txtA.read_text()
        self.assertEqual(text,
            'Hello txt a@1%2#3, touch 2')

    def test_05_03_iterChangesUnresolved(self):
        root = clientRoot
        txtA = root.joinpath('a@1%2#3.txt')
        txtE = root.joinpath('3@1%2#3.txt')

        # writable check
        commit = self.repo.getCommit(3)
        changes = list(commit.iterConflictedChanges())
        self.assertEqual(len(changes), 0)
        errorCode = (ErrorCategory.commit.value << 16) | CommitErrorCode.writable.value
        self.assertEqual(commit.lastIterResult, errorCode)

        # no unresolved
        root = clientRoot
        txtA = root.joinpath('a@1%2#3.txt')
        txtE = root.joinpath('3@1%2#3.txt')

            # create new pending changelist
        commit = self.repo.getNewCommit('tmp')
        result = commit.changeFile(
            Change(txtA.relative_to(root), ChangeType.edit,
            changeContent='Hello txt a@1%2#3, touch 3'))
        self.assertEqual(result, 0)

        result = commit.changeFile(
            Change(txtE.relative_to(root), ChangeType.add,
            changeContent='Hello txt e@1%2#3'))
        self.assertEqual(result, 0)

            # test
        changes = list(commit.iterConflictedChanges())
        self.assertEqual(len(changes), 0)
        self.assertEqual(commit.lastIterResult, 0)

        # need resolve
            # clear pendings
        result = self.repo.clearPendings()
        self.assertEqual(result, 0)
        self.assertFalse(txtE.exists())
            # create conflict 
        fileSpec = getP4ValidLocalPath(txtA)
        fileSpec1 = fileSpec + '#1'
        result = p4Run(self.repo.p4, 'sync', fileSpec1)
        self.assertNotIsInstance(result, VcsHelperErrorWrapper)

        result = commit.changeFile(
            Change(txtA.relative_to(root), ChangeType.edit,
            changeContent='Hello txt a@1%2#3, touch 3'))
        self.assertEqual(result, 0)

        result = p4Run(self.repo.p4, 'sync', fileSpec)
        self.assertNotIsInstance(result, VcsHelperErrorWrapper)

        # test
        changes = list(commit.iterConflictedChanges())
        self.assertEqual(len(changes), 1)
        self.assertEqual(commit.lastIterResult, 0)
            # reset to latest
        result = self.repo.sync(reset=True)
        self.assertEqual(result, 0)
        self.assertFalse(txtE.exists())

    def test_05_04_iterCommits(self):
        commits = list(self.repo.iterCommits())
        self.assertEqual(self.repo.lastIterResult, 0)
        self.assertEqual(len(commits), 8)
        clList = [3,4,5,7,8,9,12,13]
        for index, commit in enumerate(commits):
            self.assertFalse(commit.isWritable)
            self.assertEqual(commit.vcsData, clList[index])

        commits = list(self.repo.iterCommits(after=self.repo.getCommit(5)))
        self.assertEqual(self.repo.lastIterResult, 0)
        self.assertEqual(len(commits), 5)
        clList = [7,8,9,12,13]
        for index, commit in enumerate(commits):
            self.assertFalse(commit.isWritable)
            self.assertEqual(commit.vcsData, clList[index])

        commits = list(self.repo.iterCommits(after=self.repo.getCommit(13)))
        self.assertEqual(self.repo.lastIterResult, 0)
        self.assertEqual(len(commits), 0)


        # always put at the last test
        # hold the test, to keep the test p4 server and repo
        input("End of the test; you can check p4 repo at 127.0.0.1:1666. Press Enter to continue...")

# TODO: commit iter diff
# TODO: partial copyup / mergedown
# TODO: undo copyup / mergedown? in repo-sync?