import typing
from pathlib import Path

from ..common.logger import *
from ..common.change import ChangeType, Change
from ..common.commit import Commit, CommitErrorCode
from .p4_runner import *


VcsHelperError.registerError('common',
            ErrorCategory.commit, CommitErrorCode.wrongDepot,
            'P4 Commit "{description}" is not belong to current depot!')

class P4Commit(Commit):

    def __init__(self, repo, commit):
        super().__init__(repo, commit)

    @property
    def description(self) -> str:
        return f'P4 changelist {self.vcsData}:\n'\
            f'{self.commitRef["Description"]}'

    @property
    def vcsData(self):
        try:
            return int(self.commitRef["Change"])
        except:
            return -1       # default pending changelist

    @property
    def author(self) -> str:
        return self.commitRef['User']

    @property
    def email(self) -> str:
        userName = self.author
        return self.repo.p4.fetch_user(userName)[0]['Email']

    @property
    def isWritable(self) -> bool:
        return self.commitRef['Status'] in ['pending', 'new']

    @Commit.checkWritable()
    def changeFile(self, change: Change) -> int:
        absPath = self.repo.root.joinpath(change.path)
        destAbsPath = None
        if change.destPath is not None:
            destAbsPath = self.repo.root.joinpath(change.destPath)

        if change.changeType == ChangeType.add:
            result = change.applyChange(absPath, destAbsPath)
            if result != 0:
                return result

        p4Command = {
            ChangeType.add: 'add',
            ChangeType.edit: 'edit',
            ChangeType.delete: 'delete',
            ChangeType.move: 'edit',
        }[change.changeType]
        changelist = self.vcsData
        if changelist < 0:
            changelistArgs = {}
        else:
            changelistArgs = {'-c': self.vcsData}

        if p4Command == 'add':
            result = p4Run(self.repo.p4, p4Command, '-f',
                        absPath, **changelistArgs)
        else:
            result = p4Run(self.repo.p4, p4Command,
                        getP4ValidLocalPath(absPath), **changelistArgs)
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError()

        if change.changeType == ChangeType.move:
            result = p4Run(self.repo.p4, 'move', 
                        getP4ValidLocalPath(absPath), 
                        getP4ValidLocalPath(destAbsPath),
                        **changelistArgs)
            if isinstance(result, VcsHelperErrorWrapper):
                return result.raiseError()

        if change.changeType != ChangeType.add:
            result = change.applyChange(absPath, destAbsPath)
            if result != 0:
                return result

        return 0

    @Commit.checkWritable()
    def save(self) -> int:
        '''Save changelist with all opened changes in default pending\
 changelist, to another named changelist.'''
        
        if self.vcsData > 0:
            VcsHelperLogger.warning('Already saved! Skip saving.')
            return -1

        result = p4Fetch(self.repo.p4, 'change')
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError()
        defaultPending = result
        # no changes, just skip
        if defaultPending.get('Files', 0) == 0:
            VcsHelperLogger.warning('Empty changelist! Skip saving.')
            return -1

        # save changelist
        self.commitRef['Files'] = defaultPending['Files']
        result = p4Save(self.repo.p4, 'change', self.commitRef)
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError()
        changelist = int(result[0].split()[1])
        self.commitRef.update(self.repo.getCommit(changelist).commitRef)
        return 0
    
    @Commit.checkWritable()
    def submit(self) -> int:

        if self.vcsData == -1:
            result = self.save()
            if result != 0:
                return result

        if len(self.commitRef['Files']) == 0:
            VcsHelperLogger.warning('Empty changelist! Skip submitting.')
            return -1

        # TODO, auto resolve
        #for file in self.commitRef['Files']:
        #    result = p4Run(self.repo.p4, 'fstat', file)
        #    if isinstance(result, int):
        #        return result
        #    fstat = result[0]
        #    if 'unresolved' in fstat:
        #        print(f'"{file}" is unresolved!')
        #        hasUnresolved = True

        result = p4Run(self.repo.p4, 'submit', **{
            '-c': self.vcsData,
        })
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError()
        self.commitRef.update(self.repo.getCommit(result).commitRef)
        return 0

    def iterConflictedChanges(self) -> typing.Iterator[Change]:
        self.lastIterResult = 0
        if not self.isWritable:
            self.lastIterResult = self.error.raiseError(
                    CommitErrorCode.writable,
                    description=self.description.replace('\n', '\\n'),
                    exceptionOrExit=False,
                    returnResult=VcsHelperError.RaiseType.return_code)
            return

        clientRoot = self.repo.clientRoot
        for change in self.iterChanges():
            filePath = clientRoot.joinpath(change.path)
            filePath = getP4ValidLocalPath(filePath)
            fstat = p4Run(self.repo.p4, 'fstat', filePath)
            if isinstance(fstat, VcsHelperErrorWrapper):
                self.lastIterResult = fstat.raiseError()
                return
            if 'unresolved' in fstat[0]:
                yield change

    __changeDict = {
        'add': ChangeType.add,
        'branch': ChangeType.add,
        'edit': ChangeType.edit,
        'integrate': ChangeType.edit,
        'delete': ChangeType.delete,
    }

    def iterChanges(self) -> typing.Iterator[Change]:
        self.lastIterResult = 0

        depotRoot = self.repo.depotRoot
        clientRoot = self.repo.clientRoot
        def getLocalPath(depotPath):
            if not depotPath.startswith(depotRoot):
                VcsHelperLogger.error(f'File {depotPath} is not in current dept')
                return False
            filePath = self.repo.getLocalPath(depotPath).relative_to(clientRoot)
            filePath = Path(getLocalPathFromP4(filePath))
            return filePath

        if self.isWritable:
            # in pending changelist, use p4 opened
            result = p4Run(self.repo.p4, 'opened')
            if isinstance(result, VcsHelperErrorWrapper):
                result.raiseError(exceptionOrExit=True)
            if self.vcsData == -1:
                changelist = 'default'
            else:
                changelist = str(self.vcsData)
            for fileInfo in result:
                if fileInfo['change'] != changelist:
                    continue
                action = fileInfo['action']
                filePath = getLocalPath(fileInfo['depotFile'])
                if action in P4Commit.__changeDict:
                    yield Change(filePath, P4Commit.__changeDict[action])
                elif action == 'move/add':
                    srcPath = getLocalPath(fileInfo['movedFile'])
                    yield Change(srcPath, ChangeType.move, filePath)
        else:
            # use p4 describe
            result = p4Run(self.repo.p4, 'describe', self.vcsData)
            if isinstance(result, VcsHelperErrorWrapper):
                result.raiseError(exceptionOrExit=True)
            depotFiles = result[0].get('depotFile', [])
            actions = result[0].get('action', [])
            fromFiles = result[0].get('fromFile', [])
            if len(fromFiles) < len(actions):
                fromFiles.extend([None] * (len(actions) - len(fromFiles)))
            wrongDepot = False
            for depotFile, action, fromFile in zip(depotFiles, actions, fromFiles):
                filePath = getLocalPath(depotFile)
                if filePath == False:
                    wrongDepot = True
                    continue
                if action in P4Commit.__changeDict:
                    yield Change(filePath, P4Commit.__changeDict[action])
                elif action == 'move/add':
                    srcPath = getLocalPath(fromFile)
                    if srcPath == False:
                        wrongDepot = True
                        continue
                    yield Change(srcPath, ChangeType.move, filePath)
            if wrongDepot:
                self.lastIterResult = self.error.raiseError(
                            CommitErrorCode.wrongDepot,
                            description=self.description.replace('\n', '\\n'),
                            exceptionOrExit=False,
                            returnResult=VcsHelperError.RaiseType.return_code)

    @Commit.checkReadonly(exceptionOrExit=True)
    def iterDiffs(self,
            diffBase: typing.Optional['Commit']) -> typing.Iterator[Change]:
        '''TODO'''
        raise NotImplemented
