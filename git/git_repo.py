from pathlib import Path
import typing
from enum import Enum, auto
import git

from ..common.logger import *
from ..common.commit import Commit
from ..common.repo import Repo

from .git_commit import GitCommit


class GitRepoErrorCode(Enum):
    # connection
    open_repo_failure = 1
    init_repo_failure = auto()
    clone_repo_failure = auto()

    # remote
    remote_inexistent = auto()
    remote_branch_inexistent = auto()
    remote_branch_checkout_failure = auto()
    submodule_remote_inexistent = auto()
    
    # repo
    reset_failure = auto()

    # commit

    # tag
    tag_create_failure = auto()
    tag_delete_failure = auto()


VcsHelperError.registerError('git',
    ErrorCategory.connection, GitRepoErrorCode.open_repo_failure,
    'Failed to open git repo at "{root}"!')

VcsHelperError.registerError('git',
    ErrorCategory.connection, GitRepoErrorCode.init_repo_failure,
    'Failed to init git repo at "{root}"!')

VcsHelperError.registerError('git',
    ErrorCategory.connection, GitRepoErrorCode.clone_repo_failure,
    'Failed to clone "{url}" to "{root}" with branch "{branch}"!')

VcsHelperError.registerError('git',
    ErrorCategory.remote, GitRepoErrorCode.remote_inexistent,
    'Remote "{remote}" is inexistent!')

VcsHelperError.registerError('git',
    ErrorCategory.remote, GitRepoErrorCode.remote_branch_inexistent,
    'Remote branch "{remoteBranch}" is inexistent in remote "{remote}"!')

VcsHelperError.registerError('git',
    ErrorCategory.remote, GitRepoErrorCode.remote_branch_checkout_failure,
    'Failed to checkout Remote branch "{remoteBranch}" in remote "{remote}"!')

VcsHelperError.registerError('git',
    ErrorCategory.remote, GitRepoErrorCode.submodule_remote_inexistent,
    'Failed to find Remote branch "{remoteBranch}" for submodule "{submodule}"!')

VcsHelperError.registerError('git',
    ErrorCategory.repo, GitRepoErrorCode.reset_failure,
    'Failed to reset to "{commitSha}"!')

VcsHelperError.registerError('git',
    ErrorCategory.tag, GitRepoErrorCode.tag_create_failure,
    'Failed to create tag "{tag}"!')

VcsHelperError.registerError('git',
    ErrorCategory.tag, GitRepoErrorCode.tag_delete_failure,
    'Failed to delete tag "{tag}"!')


class GitRepo(Repo):

    def __init__(self, root: Path,
            remoteBranch: typing.Optional[str]=None):
        connectionError = VcsHelperError('git', ErrorCategory.connection)

        # git repo
        try:
            self.__repo = git.Repo(str(root))
        except Exception as e:
            print(e)
            connectionError.raiseError(
                GitRepoErrorCode.open_repo_failure,
                exceptionOrExit=True, root=root)
        
        # remote branch
        if remoteBranch is not None:
            self.setRemoteBranch(remoteBranch)
        else:
            self.clearRemoteBranch()

        # init
        super().__init__(root)

        # submodule support
        self.updateSubmodules()

    def __del__(self):
        self.__repo = None

    @property
    def remote(self):
        return self.__remote

    @property
    def remoteBranch(self):
        return self.__remoteBranch

    @property
    def head(self):
        try:
            head = self.repo.head.ref
        except:
            head = None
        return head

    @property
    def remoteBranchName(self):
        return self.__remoteBranchName

    def clearRemoteBranch(self):
        self.__remote = None
        self.__remoteBranch = None
        self.__remoteBranchName = None

    def setRemoteBranch(self, remoteBranch: str) -> int:
        remoteError = VcsHelperError('git', ErrorCategory.remote)
        remoteName, sep, self.__remoteBranchName\
                                = remoteBranch.partition('/')
        try:
            self.__remote = self.repo.remote(remoteName)
        except Exception as e:
            print(e)
            self.clearRemoteBranch()
            return remoteError.raiseError(GitRepoErrorCode.remote_inexistent,
                                                    remote=remoteName)
        try:
            self.__remoteBranch \
                        = self.__remote.refs[self.__remoteBranchName]
        except Exception as e:
            print(e)
            self.clearRemoteBranch()
            return remoteError.raiseError(GitRepoErrorCode.remote_inexistent,
                remoteName=remoteName, remoteBranch=self.__remoteBranchName)
        return 0

    def checkoutNew(self, localBranchName: str) -> int:
        remoteError = VcsHelperError('git', ErrorCategory.remote)
        try:
            head = self.repo.create_head(localBranchName, force=True)
            head.set_tracking_branch(self.remoteBranch)
            self.repo.head.ref = head
        except Exception as e:
            print(e)
            return remoteError.raiseError(
                GitRepoErrorCode.remote_branch_checkout_failure,
                remoteName=self.remote.name,
                remoteBranch=self.__remoteBranchName)
        
        result = self.sync(self.getHeadCommit(), reset=True)
        if result != 0:
            return result
        head.checkout()
        return 0

    def updateSubmodules(self) -> int:
        remoteError = VcsHelperError('git', ErrorCategory.remote)
        self.submodules = {}
        for submodule in self.__repo.submodules:
            submoduleRoot = self.root.joinpath(submodule.path)
            if self.remote is None:
                try:
                    submoduleRepo = git.Repo(str(submoduleRoot))
                except:
                    submodule.update()
                self.submodules[submodule.name] = GitRepo(submoduleRoot)
            else:
                submoduleBranchName = submodule.branch.name
                # find submodule remote branch by the same remote name
                try:
                    submoduleRemote = submodule.branch.repo.remotes[self.remote.name]
                    submoduleRemoteBranch = submoduleRemote.refs[submoduleBranchName]
                except:
                    submoduleRemoteBranch = None
                # search submodule remote branch
                if submoduleRemoteBranch is None:
                    for r in submodule.branch.repo.remotes:
                        try:
                            submoduleRemoteBranch = r.refs[submoduleBranchName]
                            break
                        except:
                            continue
                if submoduleRemoteBranch is None:
                    return remoteError.raiseError(
                        GitRepoErrorCode.submodule_remote_inexistent,
                        remoteBranch=submoduleBranchName,
                        submodule=submodule.name)
                self.submodules[submodule.name] = GitRepo(
                    submoduleRoot, submoduleRemoteBranch.name)
        return 0

    def __getTag(self, tagName: str):
        tagPath = 'refs/tags/' + tagName

        if self.remote is not None:
            try:
                self.remote.fetch(tagPath)
                hasRemote = True
            except:
                hasRemote = False
            if hasRemote:
                self.repo.delete_tag(tagName)
                self.remote.fetch(tags=True, prune_tags=True)
        
        try:
            return self.repo.tag(tagName)
        except:
            return None

    #@staticmethod
    #def check(func):
    #    def wrapper(self, *args, **kwargs):
    #        error = VcsHelperError('common', ErrorCategory.repo)
    #        if self.root is None:
    #            return error.raiseError(
    #                    RepoErrorCode.root_unset)
    #        if not self.root.exist():
    #            return error.raiseError(
    #                    RepoErrorCode.root_inexistent, root=self.root)
    #        return func(self, *args, **kwargs)
    #    return wrapper

    @staticmethod
    def initRepo(root: Path, bare: bool=False):
        try:
            git.Repo.init(str(root), bare=bare)
            return GitRepo(root)
        except Exception as e:
            print(e)
            connectionError = VcsHelperError('git', ErrorCategory.connection)
            return connectionError.raiseError(
                GitRepoErrorCode.init_repo_failure, exceptionOrExit=True,
                root=root)

    @staticmethod
    def cloneRepo(root: Path, url: typing.Union[str, Path], remoteBranch: str):
        try:
            git.Repo.clone_from(str(url), str(root), branch=remoteBranch)
            return GitRepo(root, f'origin/{remoteBranch}')
        except Exception as e:
            print(e)
            connectionError = VcsHelperError('git', ErrorCategory.connection)
            connectionError.raiseError(
                GitRepoErrorCode.clone_repo_failure, exceptionOrExit=True,
                url=url, root=root, branch=remoteBranch)

    # implement abstract methods

    @property
    def repo(self):
        return self.__repo

    @property
    def submissionType(self) -> Repo.SubmissionType:
        return Repo.SubmissionType.submitAllSaves

    @property
    def description(self) -> str:
        if self.__hasRemoteBranch:
            return f'Git Repo "{self.remote.url}" at "{self.root}"'
        else:
            return f'Git Repo at "{self.root}"'

    def clone(self, root: Path, force: bool=False, **kwargs) -> int:
        raise NotImplemented

    def sync(self, commit: Commit, reset: bool=False) -> int:
        try:
            assert isinstance(commit, GitCommit)
            if self.remote is not None:
                self.remote.fetch(prune=True)
            assert self.head is not None
            if reset:
                self.repo.head.reset(commit.commitRef, working_tree=True)
                for submoduleName, submoduleRepo in self.submodules.items():
                    submodule = self.repo.submodules[submoduleName]
                    submoduleCommit = submoduleRepo.getCommit(submodule.hexsha)
                    submoduleRepo.sync(submoduleCommit, reset=True)
            elif self.repo.head.commit != commit.commitRef:
                self.repo.head.reset(commit.commitRef)
            return 0
        except Exception as e:
            print(e)
            repoError = VcsHelperError('git', ErrorCategory.repo)
            return repoError.raiseError(GitRepoErrorCode.reset_failure,
                                                    commitSha=commit.commitSha)

    def clearPendings(self):
        self.repo.head.reset(self.repo.head.commit, working_tree=True)

    def getCommit(self, commitSha: str) -> typing.Optional[Commit]:
        try:
            commit = self.repo.commit(commitSha)
            return GitCommit(self, commit)
        except:
            return None

    def getNewCommit(self, mesg: str) -> Commit:
        # TODO
        raise NotImplementedError

    def getHeadCommit(self) -> Commit:
        if self.remote is not None:
            commit = self.remoteBranch.commit
            return GitCommit(self, commit)
        else:
            return None

    def getCommitFromTag(self, tagName: str) -> typing.Optional[Commit]:
        tag = self.__getTag(tagName)
        if tag is None:
            return None
        return GitCommit(self, tag.commit)

    def setTag(self, tagName: str, commit: Commit, mesg: str) -> int:
        tagPath = 'refs/tags/' + tagName

        if self.remote is not None:
            try:
                self.remote.fetch(tagPath)
                self.remote.push(tagPath, delete=True)
            except:
                pass

        try:
            tag = self.repo.create_tag(
                tagName, ref=commit.commitRef, message=mesg, force=True)
        except Exception as e:
            print(e)
            tagError = VcsHelperError('git', ErrorCategory.tag)
            return tagError.raiseError(
                GitRepoErrorCode.tag_create_failure, tag=tagName)
        
        if self.remote is not None:
            self.remote.push(tag.path)

        return 0

    def deleteTag(self, tagName: str):
        tagPath = 'refs/tags/' + tagName
        if self.remote is not None:
            try:
                self.remote.fetch(tagPath)
                self.remote.push(tagPath, delete=True)
            except:
                pass
        try:
            tag = self.repo.tag(tagName)
        except:
            tag = None
        if tag is not None:
            try:
                self.repo.delete_tag(tagName)
            except Exception as e:
                print(e)
                tagError = VcsHelperError('git', ErrorCategory.tag)
                return tagError.raiseError(
                    GitRepoErrorCode.tag_delete_failure, tag=tagName)

    def getTagMessage(self, tagName: str) -> typing.Optional[str]:
        tag = self.__getTag(tagName)
        if tag is None or tag.tag is None:
            return None
        return tag.tag.message

    def iterCommits(self, after: typing.Optional[Commit]
            ) -> typing.Iterator[Commit]:
        if after is None:
            iterCommitText = self.getHeadCommit().vcsData
            ancestry_path = False
        else:
            assert isinstance(after, GitCommit)
            iterCommitText = f'{self.getHeadCommit().vcsData}...{after.vcsData}'
            ancestry_path = True
        # Using --ancestry-path instead of --first-parent, because sometimes
        # one commit may be put in the second parent after merge.
        # Using --ancestry-path to get all direct commits, then filter them
        # to only keep the first parent
        ancestryCommits = list(self.repo.iter_commits(
                                iterCommitText, ancestry_path=ancestry_path))
        allParents = ancestryCommits
        if after is not None:
            allParents = ancestryCommits + [after.commitRef]
        commits = []
        firstParents = [self.getHeadCommit().commitRef]
        for commit in ancestryCommits:
            if commit in reversed(firstParents):
                commits.append(commit)
                for parent in commit.parents:
                    if parent in allParents:
                        firstParents.append(parent)
                        break

        for commit in reversed(commits):
            yield GitCommit(self, commit)

    def submit(self, commit: Commit) -> bool:
        '''TODO'''
        raise NotImplemented
