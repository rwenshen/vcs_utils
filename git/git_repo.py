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
    remote_missing = auto()
    remote_inexistent = auto()
    head_detached = auto()
    head_no_tracking_branch = auto()
    fetch_failure = auto()
    push_failure = auto()
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
    ErrorCategory.remote, GitRepoErrorCode.remote_missing,
    'No remote for the repository!')
VcsHelperError.registerError('git',
    ErrorCategory.remote, GitRepoErrorCode.remote_inexistent,
    'Remote "{remote}" is inexistent!')

VcsHelperError.registerError('git',
    ErrorCategory.remote, GitRepoErrorCode.head_detached,
    'Current repo head is detached!')
VcsHelperError.registerError('git',
    ErrorCategory.remote, GitRepoErrorCode.head_no_tracking_branch,
    'Missing tracking branch for current repo head "{name}"!')

VcsHelperError.registerError('git',
    ErrorCategory.remote, GitRepoErrorCode.fetch_failure,
    'Failed to fetch remote "{remote}"!')
VcsHelperError.registerError('git',
    ErrorCategory.remote, GitRepoErrorCode.push_failure,
    'Failed to push to remote "{remote}"!')

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


class GitProgress(git.remote.RemoteProgress):

    def __init__(self, gitOperation: str):
        super().__init__()
        VcsHelperLogger.info(f'Start git {gitOperation}')

    def update(self, op_code: int,
            cur_count: typing.Union[str, float],
            max_count: typing.Union[str, float, None] = None,
            message: str = '') -> None:
        if op_code & git.remote.RemoteProgress.COUNTING:
            op = 'Counting'
        elif op_code & git.remote.RemoteProgress.COMPRESSING:
            op = 'Compressing'
        elif op_code & git.remote.RemoteProgress.WRITING:
            op = 'Writing'
        elif op_code & git.remote.RemoteProgress.RECEIVING:
            op = 'Receiving'
        elif op_code & git.remote.RemoteProgress.RESOLVING:
            op = 'Resolving'
        elif op_code & git.remote.RemoteProgress.FINDING_SOURCES:
            op = 'Finding sources'
        elif op_code & git.remote.RemoteProgress.CHECKING_OUT:
            op = 'Checking out'

        if op_code & git.remote.RemoteProgress.END:
            VcsHelperLogger.info(f'\t{op} done; {message}')
        else:
            VcsHelperLogger.info(f'\t{op}: {cur_count} / {max_count}; {message}')


class GitRepo(Repo):

    def __init__(self, root: Path,
            remoteName: typing.Optional[str]=None,):
        connectionError = VcsHelperError('git', ErrorCategory.connection)

        # git repo
        try:
            self.__repo = git.Repo(str(root))
        except Exception as e:
            print(e)
            connectionError.raiseError(
                GitRepoErrorCode.open_repo_failure,
                exceptionOrExit=True, root=root)

        self.__remote = None
        if remoteName is not None:
            self.__remote = self.repo.remotes[remoteName]
        elif len(self.repo.remotes) > 0:
            self.__remote

        # init
        super().__init__(root)

        # submodule support
        self.submodules = {}
        #self.updateSubmodules()

    def __del__(self):
        self.__repo = None

    # repo common
    def setAuthor(self, name: str, email: str) -> int:
        writer = self.repo.config_writer('repository')
        writer.set_value('user', 'name', name)
        writer.set_value('user', 'email', email)
        writer.release()
        return 0

    # remote
    def verifyRemote(self, remoteName: typing.Optional[str]=None):
        remoteError = VcsHelperError('git', ErrorCategory.remote)
        if len(self.repo.remotes) == 0:
            return remoteError.raiseError(GitRepoErrorCode.remote_missing)
        if remoteName is not None and remoteName not in self.repo.remotes:
            return remoteError.raiseError(
                GitRepoErrorCode.remote_inexistent,
                remote=remoteName)
        return 0

    def addRemote(self, remoteName:str, url:str) -> int:
        # crate_remote
        raise NotImplementedError

    def removeRemote(self, remoteName:str) -> int:
        # 
        raise NotImplementedError

    def renameRemote(self, remoteName:str, newName:str) -> int:
        # 
        raise NotImplementedError

    # remote: tracking branch
    @property
    def isHeadDetached(self):
        return self.repo.head.is_detached

    def __getTackingBranch(self):
        if self.isHeadDetached:
            # VcsHelperLogger.warning('Head is detached, no remote tracking.')
            return None
        return self.repo.head.ref.tracking_branch()

    @property
    def trackingBranchName(self):
        trackingBranch = self.__getTackingBranch()
        if trackingBranch is None:
            return None, None
        remoteName, sep, branchName = trackingBranch.name.partition('/')
        return remoteName, branchName

    def setTrackingBranch(self, remoteName, branchName:str):
        raise NotImplementedError

    def clearTrackingBranch(self):
        raise NotImplementedError

    def verifyNonDetachedHead(self):
        remoteError = VcsHelperError('git', ErrorCategory.remote)
        if self.isHeadDetached:
            return remoteError.raiseError(GitRepoErrorCode.head_detached)
        return 0

    def verifyTrackingBranch(self):
        remoteError = VcsHelperError('git', ErrorCategory.remote)
        
        result = self.verifyNonDetachedHead()
        if result != 0:
            return result
        
        result = self.verifyRemote()
        if result != 0:
            return result
        
        if self.__getTackingBranch() is None:
            return remoteError.raiseError(
                                    GitRepoErrorCode.head_no_tracking_branch,
                                    name=self.head.ref.name)
        return 0

    # remote: fetch
    def fetch(self, remoteName: typing.Optional[str]=None, fetchAll=False):
        remoteError = VcsHelperError('git', ErrorCategory.remote)
        if remoteName is None:
            result = self.verifyTrackingBranch()
            if result != 0:
                return result
            remoteName, branchName = self.trackingBranchName

        result = self.verifyRemote(remoteName)
        if result != 0:
            return result

        if fetchAll:
            for remote in self.repo.remotes:
                try:
                    progress = GitProgress('fetch')
                    remote.fetch(progress=progress, prune=True)
                except Exception as e:
                    print(e)
                    return remoteError.raiseError(
                        GitRepoErrorCode.fetch_failure, remote=remote.name)
            return 0
        try:
            remote = self.repo.remotes[remoteName]
            remote.fetch(prune=True)
        except Exception as e:
            print(e)
            return remoteError.raiseError(
                GitRepoErrorCode.fetch_failure, remote=remote.name)
        return 0

    # remote: push head
    def push(self, remoteName: str,
            remoteBranchName: typing.Optional[str] = None) -> int:
        remoteError = VcsHelperError('git', ErrorCategory.remote)
        
        result = self.verifyRemote(remoteName)
        if result != 0:
            return result
        result = self.verifyNonDetachedHead()
        if result != 0:
            return result

        head = self.repo.head.ref
        if remoteBranchName is None:
            destPath = head.path
        else:
            destPath = 'refs/heads/' + remoteBranchName
        refSpec = f'{head.path}:{destPath}'
        remote = self.repo.remotes[remoteName]
        progress = GitProgress('push')
        try:
            result = remote.push(refSpec, progress)
        except Exception as e:
            print(e)
            return remoteError.raiseError(
                GitRepoErrorCode.push_failure, remote=remoteName)
        return 0

    # local branch
    @property
    def currentBranchName(self) -> typing.Optional[str]:
        if self.isHeadDetached:
            return None
        return self.repo.head.ref.name

    def getCurrentCommit(self) -> typing.Optional[GitCommit]:
        try:
            gitCommit = self.repo.head.commit
        except:
            return None
        return GitCommit(self, gitCommit)

    def checkoutCommit(self, Commit: GitCommit) -> int:
        raise NotImplementedError

    def checkoutLocalBranch(self, branchName: str) -> int:
        raise NotImplementedError

    def checkoutRemoteBranch(self, newBranchName: str, remoteBranchName: str) -> int:
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

        result = self.sync(self.getTopCommit(), reset=True)
        if result != 0:
            return result
        head.checkout()
        return 0

    # submodules
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

    # tags
    def __getTag(self, tagName: str):
        tagPath = 'refs/tags/' + tagName

        if self.remote is not None:
            try:
                self.remote.fetch(tagPath)
                hasRemote = True
            except:
                hasRemote = False
            if hasRemote:
                # TODO, delete tags that rejected by fetch later
                for localTag in self.repo.tags:
                    self.repo.delete_tag(localTag)
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
    def initRepo(root: Path,
            bare: bool=False,
            initialBranch: typing.Optional[str]=None):
        try:
            extraParams = {'bare': bare}
            if initialBranch is not None:
                extraParams['initial_branch'] = initialBranch
            git.Repo.init(str(root), **extraParams)
            return GitRepo(root)
        except Exception as e:
            print(e)
            connectionError = VcsHelperError('git', ErrorCategory.connection)
            return connectionError.raiseError(
                GitRepoErrorCode.init_repo_failure, exceptionOrExit=True,
                root=root)

    @staticmethod
    def cloneRepo(root: Path, url: typing.Union[str, Path],
            remoteBranch: typing.Optional[str]=None):
        try:
            extraParams = {}
            if remoteBranch is not None:
                extraParams['branch'] = remoteBranch
            progress = GitProgress('clone')
            git.Repo.clone_from(
                str(url), str(root), progress=progress, **extraParams)
            repo = GitRepo(root)
            return repo
            
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
        VcsHelperLogger.error('Not supported! please use GitRepo.cloneRepo.')
        raise NotImplementedError

    def sync(self, commit: Commit, reset: bool=False) -> int:
        try:
            assert isinstance(commit, GitCommit)
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
        try:
            return GitCommit(self, mesg=mesg)
        except:
            return None

    def getTopCommit(self) -> typing.Optional[Commit]:
        remoteBranch = self.__getTackingBranch()
        if remoteBranch is None:
            return None
        
        result = self.fetch()
        if result != 0:
            return None
        try:
            return GitCommit(self, remoteBranch.commit)
        except:
            # empty remote branch
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
            iterCommitText = self.getTopCommit().vcsData
            ancestry_path = False
        else:
            assert isinstance(after, GitCommit)
            iterCommitText = f'{self.getTopCommit().vcsData}...{after.vcsData}'
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
        firstParents = [self.getTopCommit().commitRef]
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
