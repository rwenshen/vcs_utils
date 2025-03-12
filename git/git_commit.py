import typing
from enum import Enum, auto
from pathlib import Path
import git

from ..common.logger import *
from ..common.change import ChangeType, Change
from ..common.commit import Commit, CommitErrorCode

class GitCommitErrorCode(Enum):
    add_failure = CommitErrorCode.last.value
    move_failure = auto()
    remove_failure = auto()
    multiple_writable = auto()
    commit_failure = auto()
    nothing_to_commit = auto()

VcsHelperError.registerError('git',
            ErrorCategory.commit, GitCommitErrorCode.add_failure,
            'Failed to add file "{path}"!')
VcsHelperError.registerError('git',
            ErrorCategory.commit, GitCommitErrorCode.move_failure,
            'Failed to move file "{path}" to "{dest}"!')
VcsHelperError.registerError('git',
            ErrorCategory.commit, GitCommitErrorCode.remove_failure,
            'Failed to delete file "{path}"!')
VcsHelperError.registerError('git',
            ErrorCategory.commit, GitCommitErrorCode.multiple_writable,
            'Only one writable commit is allowed!')
VcsHelperError.registerError('git',
            ErrorCategory.commit, GitCommitErrorCode.commit_failure,
            'Failed to commit!')
VcsHelperError.registerError('git',
            ErrorCategory.commit, GitCommitErrorCode.nothing_to_commit,
            'Nothing to commit!')


class GitCommit(Commit):

    __defaultIndexUsed = False

    def __init__(self, repo, 
            commit: typing.Optional[git.Commit]=None,
            mesg: typing.Optional[str]=None,
            remoteName: typing.Optional[str]=None):
        commitError = VcsHelperError('git', ErrorCategory.commit)
        # create new git index for writable commit
        if commit is None:
            commit = repo.repo.index
        super().__init__(repo, commit)
        self.__remoteName = remoteName
        if not self.__isACommit:
            # verify there is only one writable commit
            if GitCommit.__defaultIndexUsed:
                commitError.raiseError(
                    GitCommitErrorCode.multiple_writable,
                    exceptionOrExit=True)
            GitCommit.__defaultIndexUsed = True
            
            self.__mesg = mesg if mesg is not None else 'New Commit'
        else:
            self.__mesg = self.commitRef.message

    def __del__(self):
        if not self.__isACommit:
            GitCommit.__defaultIndexUsed = False

    @property
    def __isACommit(self):
        # commit type: git.Commit
        # index type: git.index.base.IndexFile
        return isinstance(self.commitRef, git.Commit)

    @property
    def description(self) -> str:
        if self.__isACommit:
            des = 'Git commit'
        else:
            des = 'Git index'
        return f'{des} {self.vcsData}:\n'\
                f'{self.__mesg}'

    @property
    def vcsData(self):
        if self.__isACommit:
            return self.commitRef.hexsha
        else:
            return self.commitRef.path

    @property
    def author(self) -> str:
        if self.__isACommit:
            return self.commitRef.author.name
        else:
            author = git.Actor.author(self.repo.repo.config_reader('repository'))
            return author.name

    @property
    def email(self) -> str:
        if self.__isACommit:
            return self.commitRef.author.email
        else:
            author = git.Actor.author(self.repo.repo.config_reader('repository'))
            return author.email

    @property
    @Commit.checkReadonly()
    def commitSha(self) -> str:
        return self.commitRef.hexsha

    @property
    def isWritable(self) -> bool:
        return not self.__isACommit

    @Commit.checkWritable()
    def changeFile(self, change: Change) -> int:
        commitError = VcsHelperError('git', ErrorCategory.commit)

        absPath = self.repo.root.joinpath(change.path)
        destAbsPath = None
        if change.destPath is not None:
            destAbsPath = self.repo.root.joinpath(change.destPath)

        def verifyResult(cmd, resultList):
            if cmd == 'add':
                f = resultList[0][4]
            elif cmd == 'remove':
                f = resultList[0]
            elif cmd == 'move':
                f, d = resultList[0]

        if change.changeType != ChangeType.move:
            result = change.applyChange(absPath, destAbsPath)
            if result != 0:
                return result

        if change.changeType in [ChangeType.add, ChangeType.edit]:
            try:
                self.commitRef.add([str(change.path)])
            except Exception as e:
                print(e)
                return commitError.raiseError(GitCommitErrorCode.add_failure,
                                                        path=str(change.path))
        elif change.changeType == ChangeType.delete:
            try:
                self.commitRef.remove([str(change.path)], working_tree=True)
            except Exception as e:
                print(e)
                return commitError.raiseError(GitCommitErrorCode.remove_failure,
                                                        path=str(change.path))
        elif change.changeType == ChangeType.move:
            try:
                self.commitRef.move([str(change.path), str(change.destPath)])
            except Exception as e:
                print(e)
                return commitError.raiseError(GitCommitErrorCode.move_failure,
                            path=str(change.path), dest=str(change.destPath))

        if change.changeType == ChangeType.move:
            result = change.applyChange(absPath, destAbsPath)
            if result != 0:
                return result

        return 0

    @Commit.checkWritable()
    def save(self) -> int:
        '''Do git commit here, commit changes to current local branch'''
        commitError = VcsHelperError('git', ErrorCategory.commit)
        # verify empty staged file list
        currentCommit = self.repo.getCurrentCommit()
        if currentCommit is None:
            if len(self.commitRef.entries) == 0:
                return commitError.raiseError(GitCommitErrorCode.nothing_to_commit)
        else:
            if len(self.commitRef.diff(currentCommit.commitRef)) == 0:
                return commitError.raiseError(GitCommitErrorCode.nothing_to_commit)
        # commit
        sha = self.commitRef.commit(self.__mesg)
        try:
            committed = self.repo.repo.commit(sha)
        except Exception as e:
            print(e)
            return commitError.raiseError(GitCommitErrorCode.commit_failure)

        self.commitRef = committed
        GitCommit.__defaultIndexUsed = False
        return 0

    def submit(self) -> int:
        '''Do git push here'''
        # commit first
        if not self.__isACommit:
            result = self.save()
            if result != 0:
                return result
        # verify non-detached
        result = self.repo.verifyNonDetachedHead()
        if result != 0:
            return result
        # push
        remoteName, branchName = self.repo.trackingBranchName
        if remoteName is None:
            remoteName = self.__remoteName
        if branchName is None:
            branchName = self.repo.currentBranchName
        result = self.repo.push(remoteName, branchName)
        return result

    def iterConflictedChanges(self) -> typing.Iterator[Change]:
        '''TODO'''
        raise NotImplemented

    def __iterTreeBlobs(self) -> typing.Iterator[str]:
        for blob in self.commitRef.tree.traverse():
            if isinstance(blob, git.objects.blob.Blob):
                yield blob.path

    def iterSubmoduleChanges(self, base: typing.Optional['Commit'],
                submodulePath: str, submoduleRepo: 'Repo'
            ) -> typing.Iterator[Change]:
        fromCommitSha = None
        toCommitSha = None
        if base is None:
            toCommitSha = submoduleRepo.head.commit.hexsha
        else:
            # get detail change
            diff = base.commitRef.diff(self.vcsData,
                                        paths=str(submodulePath),
                                        create_patch=True)[0]
            
            for line in diff.diff.split(b'\n'):
                words = line.split(b' ')
                if len(words) == 0:
                    continue
                elif words[0] == b'-Subproject':
                    fromCommitSha = words[2].decode('ascii')
                elif words[0] == b'+Subproject':
                    toCommitSha = words[2].decode('ascii')
        
        assert fromCommitSha is not None or toCommitSha is not None
        if fromCommitSha is None:
            # new added submodule
            toCommit = submoduleRepo.getCommit(toCommitSha)
            for filePath in toCommit.__iterTreeBlobs():
                yield Change(Path(submodulePath + '/' + filePath), 
                                                    ChangeType.add)
        elif toCommitSha is None:
            # deleted submodule
            fromCommit = submoduleRepo.getCommit(fromCommitSha)
            for filePath in fromCommit.__iterTreeBlobs():
                yield Change(Path(submodulePath + '/' + filePath),
                                                    ChangeType.delete)
        else:
            # modified submodule
            fromCommit = submoduleRepo.getCommit(fromCommitSha)
            toCommit = submoduleRepo.getCommit(toCommitSha)
            for change in toCommit.iterChanges(submoduleRepo, fromCommit):
                change.addParent(submodulePath)
                yield change

    def iterChanges(self) -> typing.Iterator[Change]:
        if self.__isACommit:
            pass

    def iterDiffs(self,
            fromCommit: 'Commit') -> typing.Iterator[Change]:
        return
        # get all submodules
        #submodules = {}
        #for submoduleName, submoduleRepo in self.repo.submodules.items():
        #    submodulePath = submoduleRepo.root.relative_to(self.repo.root)
        #    submodulePath = str(submodulePath).replace('\\', '/') # git style
        #    submodules[submodulePath] = submoduleRepo

        # get default base commit
        if base is None:
            if self.__isACommit:
                pass
            else:
                pass


        if base is None:
            for filePath in self.__iterTreeBlobs():
                if filePath in submodules:
                    pass
                else:
                    yield Change(Path(filePath), ChangeType.add)
        else:
            assert isinstance(base, GitCommit)
            for diff in base.commitRef.diff(self.vcsData):
                if diff.change_type in ['A', 'D', 'M']:
                    if diff.a_path in submodules:
                        yield from self.iterSubmoduleChanges(
                                base, diff.a_path, submodules[diff.a_path])
                    else:
                        yield Change(Path(diff.a_path),
                            {
                                'A': ChangeType.add,
                                'D': ChangeType.delete,
                                'M': ChangeType.edit,
                            }[diff.change_type]
                        )
                elif diff.change_type == 'R':
                    if diff.rename_to in submodules:
                        assert False, f'TODO, for moving submodule '
                        #yield from self.iterSubmoduleChanges(
                        #        base, diff.rename_to, submodules[diff.rename_to])
                    else:
                        changeType = ChangeType.move
                        yield Change(Path(diff.rename_from), changeType,
                                                    Path(diff.rename_to))
                else:
                    assert False, f'TODO, unsupported change type {diff.change_type}'
