import typing
from pathlib import Path
import git

from ..common.logger import *
from ..common.change import ChangeType, Change
from ..common.commit import Commit


class GitCommit(Commit):

    def __init__(self, repo, commit):
        super().__init__(repo, commit)

    @property
    def description(self) -> str:
        return f'Git commit {self.vcsData}:\n'\
            f'{self.commitRef.message}'

    @property
    def vcsData(self):
        return self.commitRef.hexsha

    @property
    def author(self) -> str:
        return self.commitRef.author.name

    @property
    def email(self) -> str:
        return self.commitRef.author.email

    @property
    def commitSha(self) -> str:
        return self.commitRef.hexsha

    @property
    def isWritable(self) -> bool:
        '''TODO'''
        raise NotImplemented

    def changeFile(self, change: Change):
        '''TODO'''
        assert self.isWritable
        raise NotImplemented

    def save(self) -> bool:
        '''TODO'''
        assert self.isWritable
        raise NotImplemented

    def submit(self) -> bool:
        '''TODO'''
        assert self.isWritable
        raise NotImplemented

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

    def iterChanges(self,
            base: typing.Optional['Commit']= None) -> typing.Iterator[Change]:

        assert self.repo.repo.head.commit == self.commitRef, \
            f'Please sync to {self.vcsData} first to iterate changes.'
        submodules = {}
        for submoduleName, submoduleRepo in self.repo.submodules.items():
            submodulePath = submoduleRepo.root.relative_to(self.repo.root)
            submodulePath = str(submodulePath).replace('\\', '/') # git style
            submodules[submodulePath] = submoduleRepo

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

    def iterDiffs(self,
            diffBase: typing.Optional['Commit']) -> typing.Iterator[Change]:
        '''TODO'''
        raise NotImplemented
