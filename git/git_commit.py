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
    commit_failure = auto()
    head_detached = auto()

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
            ErrorCategory.commit, GitCommitErrorCode.commit_failure,
            'Failed to commit!')


class GitCommit(Commit):

    def __init__(self, repo: 'GitRepo', 
            commit: typing.Optional[git.Commit]=None):
        commitError = VcsHelperError('git', ErrorCategory.commit)
        # create new git index for writable commit
        if commit is None:
            commit = repo.repo.index
        super().__init__(repo, commit)

    @property
    def description(self) -> str:
        if self.hasSaved:
            des = 'Git commit'
            message = self.commitRef.message
            return f'{des} {self.vcsData}:\n'\
                    f'{message}'
        else:
            des = 'Git index'
            return f'{des} {self.vcsData}'

    @property
    def vcsData(self):
        if self.hasSaved:
            return self.commitRef.hexsha
        else:
            return self.commitRef.path

    @property
    def gitAuthor(self) -> git.Actor:
        if self.hasSaved:
            return self.commitRef.author
        else:
            return self.repo.author

    @property
    def author(self) -> str:
        return self.gitAuthor.name

    @property
    def email(self) -> str:
        return self.gitAuthor.email

    @property
    def isWritable(self) -> bool:
        return not self.hasSaved

    @property
    def hasSaved(self) -> bool:
        # commit type: git.Commit
        # index type: git.index.base.IndexFile
        return isinstance(self.commitRef, git.Commit)

    @property
    def isEmpty(self) -> bool:
        if not self.hasSaved:
            localCommit = self.repo.getLocalCommit()
            if localCommit is None:
                return len(self.commitRef.entries) == 0
            else:
                diff = self.commitRef.diff(localCommit.commitRef)
                return len(diff) == 0
        else:
            return False

    @property
    def hasSubmitted(self) -> bool:
        # just check if local top commit the same as remote top, skip fetch operations
        if not self.repo.isHeadDetached:
            topCommit = self.repo.getTopCommit()
            localCommit = self.repo.getLocalCommit()
            if topCommit is not None and localCommit == topCommit:
                return True
        return False

    def checkSubmittable(self) -> int:
        errorCode = super().checkSubmittable()
        if errorCode != 0:
            return errorCode

    def changeFileImpl(self, change: Change) -> int:
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

    def saveImpl(self, message: str) -> int:
        '''Do git commit here, commit changes to current local branch'''
        commitError = VcsHelperError('git', ErrorCategory.commit)
        sha = self.commitRef.commit(message)
        try:
            committed = self.repo.repo.commit(sha)
        except Exception as e:
            print(e)
            return commitError.raiseError(GitCommitErrorCode.commit_failure)
        self.commitRef = committed
        return 0

    def submitImpl(self) -> int:
        '''Do git push here'''
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
