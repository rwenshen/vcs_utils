from pathlib import Path
import typing
from enum import Enum, auto
import git
from git.remote import PushInfo, FetchInfo

from ..common.logger import *
from ..common.commit import Commit
from ..common.repo import Repo, RepoErrorCode

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
    tracking_branch_failure = auto()
    clear_tracking_branch_failure = auto()
    remote_branch_checkout_failure = auto()
    submodule_remote_inexistent = auto()
    
    # repo
    get_author_failure = auto()
    set_author_failure = auto()
    reset_failure = RepoErrorCode.last.value
    check_out_commit_failure = auto()
    check_out_head_inexistent = auto()
    check_out_head_failure = auto()

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
    ErrorCategory.remote, GitRepoErrorCode.tracking_branch_failure,
    'Failed to tracking remote branch "{remoteBranch}"!')
VcsHelperError.registerError('git',
    ErrorCategory.remote, GitRepoErrorCode.clear_tracking_branch_failure,
    'Failed to clear tracking remote branch!')
VcsHelperError.registerError('git',
    ErrorCategory.remote, GitRepoErrorCode.remote_branch_checkout_failure,
    'Failed to checkout Remote branch "{remoteBranch}" in remote "{remote}"!')
VcsHelperError.registerError('git',
    ErrorCategory.remote, GitRepoErrorCode.submodule_remote_inexistent,
    'Failed to find Remote branch "{remoteBranch}" for submodule "{submodule}"!')

VcsHelperError.registerError('git',
    ErrorCategory.repo, GitRepoErrorCode.get_author_failure,
    'Failed to get author of git repo "{repoPath}"!')
VcsHelperError.registerError('git',
    ErrorCategory.repo, GitRepoErrorCode.set_author_failure,
    'Failed to set author of git repo "{repoPath}"!')
VcsHelperError.registerError('git',
    ErrorCategory.repo, GitRepoErrorCode.reset_failure,
    'Failed to reset to "{commitSha}"!')
VcsHelperError.registerError('git',
    ErrorCategory.repo, GitRepoErrorCode.check_out_commit_failure,
    'Failed to check out commit "{commitSha}"!')
VcsHelperError.registerError('git',
    ErrorCategory.repo, GitRepoErrorCode.check_out_head_inexistent,
    'Failed to check out head(local branch) "{headName}"! It is not existent.')
VcsHelperError.registerError('git',
    ErrorCategory.repo, GitRepoErrorCode.check_out_head_failure,
    'Failed to check out head(local branch) "{headName}"!')

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

    # headName: local branch name (if not exists, new head will be created)
    # trackingBranchPath: will be set to git repo
    # commitShaToCheckout: if headName is not set, will check out repo to detached head
    # author
    # sshFile: path to ssh; should use path in git bash (e.g. ~/user/.ssh/ssh_file)
    #           The ssh path will be set to local config
    def __init__(self, root: Path,
            headName: str|None=None,
            commitShaToCheckout: str|None=None,
            author: git.Actor|None=None,
            sshFile: Path|None=None):
        # create git repo
        try:
            self.__repo = git.Repo(str(root))
        except Exception as e:
            print(e)
            self.connectionError.raiseError(
                                        GitRepoErrorCode.open_repo_failure,
                                        exceptionOrExit=True, root=root)

        # ssh
        self.__oldEnv = None
        if sshFile is not None:
            sshCmd = f'ssh -i {sshFile}'
            self.__oldEnv = git.Git().update_environment(GIT_SSH_COMMAND=sshCmd)

        # author
        try:
            self.__author = git.Actor.author(
                                    self.repo.config_reader('repository'))
        except Exception as e:
            print(e)
            self.connectionError.raiseError(
                                        GitRepoErrorCode.get_author_failure,
                                        exceptionOrExit=True, repoPath=root)
        if author is not None:
            self.author = author

        # ssh
        if sshFile is not None:
            config = self.repo.config_writer('repository')
            config.set_value('core', 'sshCommand', f'ssh -i {sshFile}')

        # head (local branch / detached head)
        if headName is not None:
            try:
                headRef = self.repo.heads[headName]
            except Exception as e:
                pass # create new
            else:
                self.checkoutHead(headName)
            if commitShaToCheckout is not None:
                VcsHelperLogger.warning(
                    "commitShaToCheckout '%s' is ignores, because headName is set.", commitShaToCheckout)
        elif commitShaToCheckout is not None:
            self.checkoutCommit(self.getCommit(commitShaToCheckout))

        # super init
        super().__init__(root)

        # submodule support
        self.submodules = {}
        #self.updateSubmodules()

    def __del__(self):
        self.__repo = None
        if self.__oldEnv is not None:
            git.Git().update_environment(**self.__oldEnv)

    # errors
    @property
    def connectionError(self):
        return VcsHelperError('git', ErrorCategory.connection)
    @property
    def repoError(self):
        return VcsHelperError('git', ErrorCategory.repo)
    @property
    def remoteError(self):
        return VcsHelperError('git', ErrorCategory.remote)

    # repo author
    @property
    def author(self) -> git.Actor:
        return self.__author

    # save author name and email, to local
    def setAuthorNameAndEmail(self, name: str, email: str):
        try:
            writer = self.repo.config_writer('repository')
            writer.set_value('user', 'name', name)
            writer.set_value('user', 'email', email)
            writer.release()
        except Exception as e:
            print(e)
            return self.connectionError.raiseError(
                                        GitRepoErrorCode.set_author_failure,
                                        exceptionOrExit=True,
                                        repoPath=self.repo.working_dir)
        self.__author.name = name
        self.__author.email = email

    # remote
    def verifyRemote(self) -> int:
        if len(self.repo.remotes) == 0:
            return self.remoteError.raiseError(GitRepoErrorCode.remote_missing)
        return 0

    def verifyGetRemoteName(self, remoteName: str|None=None) -> str|int:
        errorCode = self.verifyRemote()
        if errorCode != 0:
            return errorCode
        if remoteName is not None:
            if remoteName not in self.repo.remotes:
                return self.remoteError.raiseError(
                                        GitRepoErrorCode.remote_inexistent,
                                        remote=remoteName)
            else:
                return remoteName
        else:
            trackingBranchPath = self.trackingBranchPath
            if trackingBranchPath is None:
                return self.repo.remotes[0]
            remoteName, sep, branchName = trackingBranchPath.partition('/')
            return remoteName

    def addRemote(self, remoteName:str, url:str) -> int:
        # create_remote
        raise NotImplementedError

    def removeRemote(self, remoteName:str) -> int:
        # 
        raise NotImplementedError

    def renameRemote(self, remoteName:str, newName:str) -> int:
        # 
        raise NotImplementedError

    # remote: tracking branch
    def __getTackingBranch(self) -> git.RemoteReference|None:
        if self.isHeadDetached:
            return None
        return self.repo.head.ref.tracking_branch()

    @property
    def trackingBranchPath(self) -> str|None:
        trackingBranch = self.__getTackingBranch()
        if trackingBranch is None:
            return None
        return str(trackingBranch)

    def setTrackingBranchPath(self, trackingBranchPath:str|None) -> int:
        # check head detached
        result = self.verifyNonDetachedHead()
        if result != 0:
            return result
        # no change
        if self.trackingBranchPath == trackingBranchPath:
            return 0
        # get tracking branch
        if trackingBranchPath is None:
            remoteBranch = None
        else:
            remoteName, sep, branchName = trackingBranchPath.partition('/')
            result = self.verifyGetRemoteName(remoteName)
            if isinstance(result, int):
                return result
            try:
                remoteBranch = self.repo.remotes[0].refs[branchName]
            except Exception as e:
                print(e)
                return self.remoteError.raiseError(
                                GitRepoErrorCode.remote_branch_inexistent,
                                remote=remoteName,
                                remoteBranch=branchName)
        # do tracking
        try:
            self.repo.head.ref.set_tracking_branch(remoteBranch)
        except Exception as e:
            print(e)
            if remoteBranch is None:
                return self.remoteError.raiseError(
                            GitRepoErrorCode.clear_tracking_branch_failure)
            else:
                return self.remoteError.raiseError(
                            GitRepoErrorCode.tracking_branch_failure,
                            remoteBranch=branchName)
        return 0

    def verifyNonDetachedHead(self) -> int:
        if self.isHeadDetached:
            return self.remoteError.raiseError(GitRepoErrorCode.head_detached)
        return 0

    def verifyTrackingBranch(self):
        result = self.verifyNonDetachedHead()
        if result != 0:
            return result
        result = self.verifyRemote()
        if result != 0:
            return result
        if self.__getTackingBranch() is None:
            return self.remoteError.raiseError(
                                    GitRepoErrorCode.head_no_tracking_branch,
                                    name=self.head.ref.name)
        return 0

    def checkoutRemoteBranch(self, headName: str, remoteBranchName: str) -> int:
        # TODO
        try:
            head = self.repo.create_head(localBranchName, force=True)
            head.set_tracking_branch(self.remoteBranch)
            self.repo.head.ref = head
        except Exception as e:
            print(e)
            return self.remoteError.raiseError(
                GitRepoErrorCode.remote_branch_checkout_failure,
                remoteName=self.remote.name,
                remoteBranch=self.__remoteBranchName)

        result = self.sync(self.getTopCommit(), reset=True)
        if result != 0:
            return result
        head.checkout()
        return 0

    # remote: fetch
    def fetch(self, remoteName: str|None=None, fetchAll: bool=False) -> int:

        def doFetch(remote: git.Remote) -> int:
            try:
                progress = GitProgress('fetch')
                fetchInfos: typing.Iterable[FetchInfo] = remote.fetch(
                                                progress=progress, prune=True)
                for fetchInfo in fetchInfos:
                    assert (fetchInfo.flags & (
                        FetchInfo.ERROR | FetchInfo.REJECTED)) == 0
            except Exception as e:
                print(e)
                return self.remoteError.raiseError(
                    GitRepoErrorCode.fetch_failure, remote=remote.name)
            return 0

        if fetchAll:
            result = self.verifyRemote()
            if result != 0:
                return result
            for remote in self.repo.remotes:
                errorCode = doFetch(remote)
                if errorCode != 0:
                    return errorCode
            return 0
        
        result = self.verifyGetRemoteName(remoteName)
        if isinstance(result, int):
            return result
        remote = self.repo.remotes[result]
        return doFetch(remote)

    # remote: push head
    def push(self, remoteName: str|None=None,
            remoteBranchName: str|None=None) -> int:
        # get remote
        result = self.verifyGetRemoteName(remoteName)
        if isinstance(result, int):
            return result
        remote = self.repo.remotes[result]
        # src branch
        errorCode = self.verifyNonDetachedHead()
        if errorCode != 0:
            return errorCode
        srcBranch = str(self.repo.head.ref)
        # dest branch
        destBranch = None
        if remoteBranchName is not None:
            destBranch = remoteBranchName

        refSpec = srcBranch
        if destBranch is not None:
            refSpec += f':{destBranch}'
        progress = GitProgress('push')
        try:
            pushInfo = remote.push(refSpec, progress)[0]
            assert (pushInfo.flags & (
                PushInfo.NEW_HEAD | PushInfo.FAST_FORWARD | PushInfo.NEW_TAG))
        except Exception as e:
            print(e)
            return self.remoteError.raiseError(
                GitRepoErrorCode.push_failure, remote=remoteName)
        return 0

    # head (local branch / detached head)
    @property
    def isHeadDetached(self) -> bool:
        return self.repo.head.is_detached

    @property
    def headName(self) -> str|None:
        if self.isHeadDetached:
            return None
        return str(self.repo.head.ref)

    def renameHead(self, newName: str) -> int
        raise NotImplemented

    def createHead(self, name: str, commit: GitCommit|None) -> int:
        raise NotImplemented

    def deleteHead(self, name: str) -> int:
        raise NotImplemented

    def getHeadCommit(self) -> GitCommit|None:
        try:
            gitCommit = self.repo.head.commit
        except:
            return None
        return GitCommit(self, gitCommit)

    def checkoutCommit(self, commit: GitCommit) -> int:
        if self.isHeadDetached and self.repo.head.commit == commit.commitRef:
            return 0 # already on the commit
        # check readonly
        errorCode = commit.checkReadOnly()
        if errorCode != 0:
            return errorCode
        # do check out
        try:
            self.repo.head.set_reference(commit.commitRef)
        except Exception as e:
            print(e)
            return self.repoError.raiseError(
                GitRepoErrorCode.check_out_commit_failure,
                commitSha=commit.vcsData)
        return 0

    def checkoutHead(self, headName: str) -> int:
        if not self.isHeadDetached and str(self.repo.head.ref) == headName:
            return 0 # already on the head
        try:
            headRef = self.repo.heads[headName]
        except Exception as e:
            print(e)
            return self.repoError.raiseError(
                GitRepoErrorCode.check_out_head_inexistent,
                headName=headName)
        try:
            self.repo.head.set_reference(headRef)
        except Exception as e:
            print(e)
            return self.repoError.raiseError(
                GitRepoErrorCode.check_out_head_failure,
                headName=headName)
        return 0

    # submodules
    def updateSubmodules(self) -> int:
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
                    return self.remoteError.raiseError(
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

    @staticmethod
    def initRepo(root: Path,
            bare: bool=False,
            initialBranch: str|None=None) -> 'GitRepo':
        try:
            extraParams = {'bare': bare}
            if initialBranch is not None:
                extraParams['initial_branch'] = initialBranch
            git.Repo.init(str(root), **extraParams)
            return GitRepo(root, headName=initialBranch)
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
            return self.repoError.raiseError(GitRepoErrorCode.reset_failure,
                                                    commitSha=commit.vcsData)

    def clearPendings(self):
        self.repo.head.reset(self.repo.head.commit, working_tree=True)

    def getCommit(self, commitSha: str) -> typing.Optional[Commit]:
        try:
            commit = self.repo.commit(commitSha)
            return GitCommit(self, commit)
        except:
            return None

    def getNewCommit(self) -> Commit|None:
        try:
            return GitCommit(self)
        except:
            return None

    def getTopCommit(self) -> Commit|None:
        # get remote branch
        trackingBranch = self.__getTackingBranch()
        if trackingBranch is None:
            return None
        # fetch
        result = self.fetch()
        if result != 0:
            return None

        try:
            return GitCommit(self, trackingBranch.commit)
        except:
            # empty remote branch
            return None

    def getCommitFromTag(self, tagName: str) -> Commit|None:
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
