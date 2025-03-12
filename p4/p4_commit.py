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
        #    result = p4Run(self.repo.p4, 'fstat',
        #                   getP4ValidLocalPath(file))
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

    def __getPendingChangelist(self):
        if self.vcsData == -1:
            changelist = 'default'
        else:
            changelist = str(self.vcsData)
        return changelist

    def __getLocalPath(self, depotPath):
        depotRoot = self.repo.depotRoot
        clientRoot = self.repo.clientRoot
        if not depotPath.startswith(depotRoot):
            VcsHelperLogger.error(f'File {depotPath} is not in current dept')
            return False
        filePath = self.repo.getLocalPath(depotPath).relative_to(clientRoot)
        filePath = Path(getLocalPathFromP4(filePath))
        return filePath

    # in pending changelist, use p4 opened
    def __iterPendingChangelist(self, changelist):
        result = p4Run(self.repo.p4, 'opened')
        if isinstance(result, VcsHelperErrorWrapper):
            result.raiseError(exceptionOrExit=True)
        for fileInfo in result:
            if fileInfo['change'] != changelist:
                continue
            action = fileInfo['action']
            filePath = self.__getLocalPath(fileInfo['depotFile'])
            if action in P4Commit.__changeDict:
                yield Change(filePath, P4Commit.__changeDict[action])
            elif action == 'move/add':
                srcPath = self.__getLocalPath(fileInfo['movedFile'])
                yield Change(srcPath, ChangeType.move, filePath)

    # use p4 describe
    def __iterSubmittedChangelist(self, changelist):
        result = p4Run(self.repo.p4, 'describe', changelist)
        if isinstance(result, VcsHelperErrorWrapper):
            result.raiseError(exceptionOrExit=True)
        depotFiles = result[0].get('depotFile', [])
        actions = result[0].get('action', [])
        fromFiles = result[0].get('fromFile', [])
        if len(fromFiles) < len(actions):
            fromFiles.extend([None] * (len(actions) - len(fromFiles)))
        wrongDepot = False
        for depotFile, action, fromFile in zip(depotFiles, actions, fromFiles):
            filePath = self.__getLocalPath(depotFile)
            if filePath == False:
                wrongDepot = True
                continue
            if action in P4Commit.__changeDict:
                yield Change(filePath, P4Commit.__changeDict[action])
            elif action == 'move/add':
                srcPath = self.__getLocalPath(fromFile)
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

    def iterChanges(self) -> typing.Iterator[Change]:
        self.lastIterResult = 0

        if self.isWritable:
            changelist = self.__getPendingChangelist()
            yield from self.__iterPendingChangelist(changelist)
        else:
            yield from self.__iterSubmittedChangelist(self.vcsData)

    #def iterChangesP4(self):
    #    # TODO
    #    pass

    def __iterChangesFromTo(self,
            fromChangelist: int, fromPendingChangelist: typing.Optional[str],
            toChangelist: int, toPendingChangelist: typing.Optional[str]):
        def inverseChange(change: Change):
            if change.changeType == ChangeType.add:
                return Change(change.path, ChangeType.delete)
            elif change.changeType == ChangeType.delete:
                return Change(change.path, ChangeType.add)
            elif change.changeType == ChangeType.move:
                return Change(change.destPath, change.changeType, change.path)
            else:
                return change
        # from pending changelist, do inverse change
        if fromPendingChangelist is not None:
            for change in self.__iterPendingChangelist(fromPendingChangelist):
                yield inverseChange(change)
        # submitted changes
        if toChangelist != fromChangelist:
            root = getP4ValidLocalPath(self.repo.root.joinpath('...'))
            needReverse = False
            if toChangelist < fromChangelist:
                needReverse = True
            if needReverse:
                fileSpec = f'{root}@{toChangelist},{fromChangelist}'
            else:
                fileSpec = f'{root}@{fromChangelist},{toChangelist}'
            results = p4Run(self.repo.p4, 'changes', fileSpec)
            if needReverse:
                p4Changes = results
            else:
                p4Changes = reversed(results)
            for p4Change in p4Changes:
                changelist = p4Change['change']
                for change in self.__iterSubmittedChangelist(changelist):
                    if needReverse:
                        yield inverseChange(change)
                    else:
                        yield change
        # to pending changelist
        if toPendingChangelist is not None:
            yield from self.__iterPendingChangelist(toPendingChangelist)

    def __handleChangesForDiff(self, changes):
        # status
        handledChangeDict = {}
        def getHandlerKey(file: Path, thisChange: Change,
                lastChange: typing.Optional[Change]):
            def getKeyFromChange(file: Path,
                    change: typing.Optional[Change]) ->str:
                if change is None:
                    return None
                key = change.changeType.name
                if change.changeType == ChangeType.move:
                    if file == change.destPath:
                        key += '_dest'
                return key
            key1 = getKeyFromChange(file, thisChange)
            key2 = getKeyFromChange(file, lastChange)
            return key1, key2

        def handleFileChange(file: Path, change: Change):
            lastChange = handledChangeDict.get(file, [None])[-1]
            key = getHandlerKey(file, change, lastChange)
            handler = changeHandlerDict[key]
            handler(key, file, change, lastChange)

        # change handlers
        def doNothing():
            pass

        def clearLastChange(file: Path):
            changes = handledChangeDict[file]
            del changes[-1]
            if len(changes) == 0:
                del handledChangeDict[file]

        def addFileChange(file: Path, change: Change):
            changes = handledChangeDict.setdefault(file, [])
            changes.append(change)

        def replaceFileChange(file: Path, change: Change):
            if file in handledChangeDict:
                clearLastChange(file)
            addFileChange(file, change)

        def addSingleFileChange(file: Path, changeType: ChangeType):
            addFileChange(file, Change(file, changeType))

        def replaceSingleFileChange(file: Path, changeType: ChangeType,):
            replaceFileChange(file, Change(file, changeType))

        def handleImpossible(key):
            if key[1] is None:
                assert False, f'Impossible to "{key[0]}" for a new file.'
            else:
                assert False, f'Impossible to handle "{key[0]}" after "{key[1]}"'

        def handleDelMoved(file: Path, lastChange: Change):
            srcFile = lastChange.path
            replaceSingleFileChange(srcFile, ChangeType.delete)
            clearLastChange(file)

        def handleMoveFrom(file: Path, change: Change):
            replaceFileChange(file, change)
            handleFileChange(change.destPath, change)

        def handleMoveAdded(file:Path, change: Change):
            clearLastChange(file)
            newChange = Change(change.destPath, ChangeType.add)
            handleFileChange(newChange.path, newChange)

        def handleMoveMultiple(file:Path, change: Change, lastChange: Change):
            finalDest = change.destPath
            preSrc = lastChange.path
            if preSrc == finalDest:
                # set preSrc as edit
                preSrcChanges = handledChangeDict[preSrc]
                assert len(preSrcChanges) == 1
                c = preSrcChanges[0]
                assert c.changeType == ChangeType.move
                assert c.destPath == file
                newChange = Change(preSrc, ChangeType.edit)
                replaceFileChange(preSrc, newChange)
                # skip dest
            else:
                preSrcChanges = handledChangeDict[preSrc]
                newChange = Change(preSrc, ChangeType.move, finalDest)
                # link previous move dest to new dest
                for index, c in enumerate(reversed(preSrcChanges)):
                    index = len(preSrcChanges) - index - 1
                    if c.changeType == ChangeType.move:
                        assert c.destPath == file
                        preSrcChanges[index] = newChange
                        break
                clearLastChange(file)
                # new dest
                handleFileChange(finalDest, newChange)

        changeHandlerDict = {
            ('add', None): lambda key, file, change, lastChange:\
                                addSingleFileChange(file, ChangeType.add),
            ('add', 'add'): lambda key, file, change, lastChange:\
                                handleImpossible(key),
            ('add', 'edit'): lambda key, file, change, lastChange:\
                                handleImpossible(key),
            ('add', 'delete'): lambda key, file, change, lastChange:\
                                replaceSingleFileChange(file, ChangeType.add),
            ('add', 'move'): lambda key, file, change, lastChange:\
                                addSingleFileChange(file, ChangeType.add),
            ('add', 'move_dest'): lambda key, file, change, lastChange:\
                                handleImpossible(key),

            ('edit', None): lambda key, file, change, lastChange:\
                                addSingleFileChange(file, ChangeType.edit),
            ('edit', 'add'): lambda key, file, change, lastChange:\
                                doNothing(),
            ('edit', 'edit'): lambda key, file, change, lastChange:\
                                doNothing(),
            ('edit', 'delete'): lambda key, file, change, lastChange:\
                                handleImpossible(key),
            ('edit', 'move'): lambda key, file, change, lastChange:\
                                handleImpossible(key),
            ('edit', 'move_dest'): lambda key, file, change, lastChange:\
                                doNothing(),

            ('delete', None): lambda key, file, change, lastChange:\
                                addSingleFileChange(file, ChangeType.delete),
            ('delete', 'add'): lambda key, file, change, lastChange:\
                                clearLastChange(file),
            ('delete', 'edit'): lambda key, file, change, lastChange:\
                                addSingleFileChange(file, ChangeType.delete),
            ('delete', 'delete'): lambda key, file, change, lastChange:\
                                handleImpossible(key),
            ('delete', 'move'): lambda key, file, change, lastChange:\
                                handleImpossible(key),
            ('delete', 'move_dest'): lambda key, file, change, lastChange:\
                                handleDelMoved(file, lastChange),

            ('move', None): lambda key, file, change, lastChange:\
                                handleMoveFrom(file, change),
            ('move', 'add'): lambda key, file, change, lastChange:\
                                handleMoveAdded(file, change),
            ('move', 'edit'): lambda key, file, change, lastChange:\
                                handleMoveFrom(file, change),
            ('move', 'delete'): lambda key, file, change, lastChange:\
                                handleImpossible(key),
            ('move', 'move'): lambda key, file, change, lastChange:\
                                handleImpossible(key),
            ('move', 'move_dest'): lambda key, file, change, lastChange:\
                                handleMoveMultiple(file, change, lastChange),

            ('move_dest', None): lambda key, file, change, lastChange:\
                                addFileChange(file, change),
            ('move_dest', 'add'): lambda key, file, change, lastChange:\
                                handleImpossible(key),
            ('move_dest', 'edit'): lambda key, file, change, lastChange:\
                                handleImpossible(key),
            ('move_dest', 'delete'): lambda key, file, change, lastChange:\
                                addFileChange(file, change),
            ('move_dest', 'move'): lambda key, file, change, lastChange:\
                                addFileChange(file, change),
            ('move_dest', 'move_dest'): lambda key, file, change, lastChange:\
                                handleImpossible(key),
        }

        # handle changes
        for change in changes:
            print(change)
            handleFileChange(change.path, change)
        print(handledChangeDict)
        return handledChangeDict

    # Mostly used for cross-vcs-tool operation.
    # for p4-p4 operation, please use iterChangesP4 instead.
    def iterDiffs(self,
            fromCommit: 'Commit') -> typing.Iterator[Change]:
        # prepare
        if self.isWritable:
            toPendingChangelist = self.__getPendingChangelist()
            toChangelist = self.repo.getTopCommit().vcsData
        else:
            toPendingChangelist = None
            toChangelist = self.vcsData
        if fromCommit.isWritable:
            fromPendingChangelist = fromCommit.__getPendingChangelist()
            fromChangelist = self.repo.getTopCommit().vcsData
        else:
            fromPendingChangelist = None
            fromChangelist = fromCommit.vcsData
        
        # handle changes to diff
        changes = self.__iterChangesFromTo(
                fromChangelist, fromPendingChangelist,
                toChangelist, toPendingChangelist)
        handledChangeDict = self.__handleChangesForDiff(changes)
        
        # final result
        moveFromHandledSet = set()
        moveToHandledSet = set()
        for file, changes in handledChangeDict.items():
            for change in changes:
                if change.changeType != ChangeType.move:
                    yield change
                else:
                    if change.path == file and file not in moveFromHandledSet:
                        moveFromHandledSet.add(file)
                        moveToHandledSet.add(change.destPath)
                        yield change
                    elif change.destPath == file and file not in moveToHandledSet:
                        handled = False
                        for srcChange in handledChangeDict[change.path]:
                            if srcChange.changeType == ChangeType.move \
                                    and srcChange.path == change.path \
                                    and srcChange.destPath == file:
                                moveFromHandledSet.add(srcChange.path)
                                moveToHandledSet.add(file)
                                yield srcChange
                                handled = True
                                break
                        assert handled, "Impossible"
                    # skip handled
                    continue
