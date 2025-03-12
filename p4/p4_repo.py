from enum import Enum, auto
from os import unlink
from pathlib import Path
import typing
import getpass
from P4 import P4

from ..common.logger import *
from ..common.commit import Commit
from ..common.repo import Repo
from .p4_runner import *
from .p4_commit import P4Commit


class P4RepoErrorCode(Enum):
    # connection
    connection_failure = 1
    login_failure = auto()

    # repo
        # client
    client_invalid = 1
    client_inexistent = auto()
        # repo init
    root_invalid = 0x100
    root_not_empty = auto()
        # stream
    not_a_stream_client = 0x200
    stream_inexistent = auto()
    stream_not_parent = auto()
    stream_no_parent = auto()

    # tag
    tag_to_pending = 0x100

VcsHelperError.registerError('p4',
    ErrorCategory.connection, P4RepoErrorCode.connection_failure,
    'Failed to connect to P4!')
VcsHelperError.registerError('p4',
    ErrorCategory.connection, P4RepoErrorCode.login_failure,
    'Failed to login P4!')

VcsHelperError.registerError('p4',
    ErrorCategory.repo, P4RepoErrorCode.client_invalid,
    'Client {client} is invalid!')
VcsHelperError.registerError('p4',
    ErrorCategory.repo, P4RepoErrorCode.client_inexistent,
    'Client {client} is inexistent!')
VcsHelperError.registerError('p4',
    ErrorCategory.repo, P4RepoErrorCode.root_invalid,
    'Root "{root}" is invalid!')
VcsHelperError.registerError('p4',
    ErrorCategory.repo, P4RepoErrorCode.root_not_empty,
    'Root "{root}" is not empty!')
VcsHelperError.registerError('p4',
    ErrorCategory.repo, P4RepoErrorCode.not_a_stream_client,
    'Client "{client}" is not a stream client!')
VcsHelperError.registerError('p4',
    ErrorCategory.repo, P4RepoErrorCode.stream_inexistent,
    'Stream "{stream}" is inexistent!')
VcsHelperError.registerError('p4',
    ErrorCategory.repo, P4RepoErrorCode.stream_not_parent,
    'Stream "{parent}" is not the parent of stream {stream}!')
VcsHelperError.registerError('p4',
    ErrorCategory.repo, P4RepoErrorCode.stream_no_parent,
    'Stream "{stream}" has no parent!')

VcsHelperError.registerError('p4', ErrorCategory.tag, 0x100,
    'Cannot tag a pending changelist!')


class P4Repo(Repo):

    def __init__(self,
            p4Port: typing.Optional[str] = None,
            p4User: typing.Optional[str] = None,
            p4Client: typing.Optional[str] = None):
        connectionError = VcsHelperError('p4', ErrorCategory.connection)

        # connect P4
        self.__p4 = P4()
        if p4Port is not None:
            self.p4.port = p4Port
        if p4User is not None:
            self.p4.user = p4User
        if p4Client is not None:
            self.p4.client = p4Client
        try:
            self.p4.connect()
        except Exception as e:
            connectionError.raiseError(P4RepoErrorCode.connection_failure,
                                                        exceptionOrExit=True)
        assert self.p4.connected(), 'Impossible'

        # login
        needPassword = False
        try:
            self.p4.run_opened()
        except:
            needPassword = True
        if needPassword:
            password = getpass.getpass()
            try:
                self.p4.run_login(password=password)
                VcsHelperLogger.info('P4 is logged in.')
            except Exception as e:
                connectionError.raiseError(P4RepoErrorCode.login_failure,
                                                        exceptionOrExit=True)

        # add log
        self.p4.logger = VcsHelperLogger

        # update client
        self.__updateClient(exceptionOrExit=True)

    def __updateClient(self, exceptionOrExit=False) -> int:
        result = p4Run(self.p4, 'info')
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError(exceptionOrExit=exceptionOrExit)
        self.__info =  result[0]
        VcsHelperLogger.info(str(self.__info))
        super().__init__(self.clientRoot)

        self.__description = f'P4 Repo\n\tPort: {self.p4.port}\n'
        if self.clientRoot is not None:
            if 'clientStream' in self.__info:
                self.__description += f'\tStream: {self.__info["clientStream"]}'
            else:
                result = p4Fetch(self.p4, 'client')
                if isinstance(result, VcsHelperErrorWrapper):
                    return result.raiseError(exceptionOrExit=exceptionOrExit)
                self.__description += '\tViews:'
                for view in result['View']:
                    self.__description += '\n'
                    self.__description += f'\t\t{view}'
            self.__description += '\n'
        return 0

    def __del__(self):
        if self.__p4 is not None and self.__p4.connected():
            self.__p4.disconnect()

    @property
    def p4(self):
        return self.__p4

    @property
    def client(self) -> str:
        return self.p4.client

    @property
    def clientRoot(self) -> typing.Optional[Path]:
        path = self.__info.get('clientRoot', None)
        if path is None:
            return None
        return Path(path)

    @property
    def userName(self) -> str:
        return self.p4.user

    @property
    def depotRoot(self) -> typing.Optional[Path]:
        depotRoot = self.getDepotPath(self.clientRoot.joinpath('...'))
        return depotRoot[:-4]

    def getDepotPath(self, localPath: Path) -> typing.Optional[str]:
        result = p4Run(self.p4, 'where',
                        getP4ValidLocalPath(localPath))
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError(returnResult=None)
        return result[0]['depotFile']

    def getLocalPath(self, depotPath: str) -> typing.Optional[Path]:
        result = p4Run(self.p4, 'where',
                        getP4ValidLocalPath(depotPath))
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError(returnResult=None)
        return Path(result[0]['path'])

    @staticmethod
    def checkClient(exceptionOrExit: bool=False,
            returnResult=VcsHelperError.RaiseType.return_code):
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                error = VcsHelperError('p4', ErrorCategory.connection)
                if self.clientRoot is None:
                    return error.raiseError(P4RepoErrorCode.client_invalid,
                        exceptionOrExit=exceptionOrExit,
                        returnResult=returnResult)
                return func(self, *args, **kwargs)
            return wrapper
        return decorator

    # p4 specific methods
    def updateSpec(self, spec: str, specName: str, args: dict={},
            **options) -> int:
        result = p4Fetch(self.p4, spec, specName, **args)
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError()
        for key, value in options.items():
            if value is None:
                if key in result:
                    del result[key]
            else:
                result[key]=value
        result = p4Save(self.p4, spec, result)
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError()
        return 0

    def deleteSpec(self, spec: str, specName: str, force: bool=False) -> int:
        args = {'-d': True}
        if force:
            args['-f'] = True
        result = p4Run(self.p4, spec, specName, **args)
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError()
        VcsHelperLogger.info(result[0])
        return 0

    def updateDepot(self, depotName: str, depotType: str='local',
            **options) -> int:
        return self.updateSpec('depot', depotName, {'-t': depotType}, **options)

    def deleteDepot(self, depotName: str, force: bool=False) -> int:
        return self.deleteSpec('depot', depotName, force)

    def updateStream(self, streamName: str, streamType: str,
            parent: typing.Optional[str]=None,
            parentView: str='inherit',
            **options) -> int:
        args = {
            '-t': streamType,
            '--parentview': parentView,
        }
        if parent is not None:
            args['-P'] = parent
        return self.updateSpec('stream', streamName, args, *options)

    def deleteStream(self, streamName: str, force: bool=False) -> int:
        return self.deleteSpec('stream', streamName, force)

    def __getStreamFromClient(self, clientName: str
            ) -> typing.Union[dict, VcsHelperErrorWrapper]:
        client = p4Fetch(self.p4, 'client', clientName)
        if isinstance(client, VcsHelperErrorWrapper):
            return client
        if 'Access' not in client:
            return VcsHelperErrorWrapper('p4', ErrorCategory.repo,
                        P4RepoErrorCode.client_inexistent, client=clientName)
        if 'Stream' not in client:
            return VcsHelperErrorWrapper('p4', ErrorCategory.repo,
                    P4RepoErrorCode.not_a_stream_client, client=clientName)
        return self.__getStream(client['Stream'])

    def __getStream(self, streamName: str
            ) -> typing.Union[dict, VcsHelperErrorWrapper]:
        stream = p4Fetch(self.p4, 'stream', streamName)
        if isinstance(stream, VcsHelperErrorWrapper):
            return stream
        if 'Access' not in stream:
            return VcsHelperErrorWrapper('p4', ErrorCategory.repo,
                        P4RepoErrorCode.stream_inexistent, stream=streamName)
        return stream

    @checkClient.__func__()
    def switchStream(self, newStream: str,
            sync: bool=False, reset: bool=False) -> int:
        stream = self.__getStreamFromClient(self.client)
        if isinstance(stream, VcsHelperErrorWrapper):
            return stream.raiseError()
        
        result = self.updateSpec('client', self.client, Stream=newStream)
        if result != 0:
            return result
        if sync:
            result = self.sync(reset=reset)
        return result

    def __getStreamHead(self, stream: str) -> Commit:
        result = p4Run(self.p4, 'changes',
            str(stream + '/...'),
            **{
                '-s': 'submitted',
                '-m': 1,
            }
        )
        if isinstance(result, VcsHelperErrorWrapper):
            result.raiseError(exceptionOrExit=True)
        changelist = result[0]['change']
        return self.getCommit(changelist)

    @checkClient.__func__()
    def streamCopyUp(self, srcStreamName: str,
            commit: typing.Optional[Commit]=None) -> typing.Optional[Commit]:
        stream = self.__getStreamFromClient(self.client)
        if isinstance(stream, VcsHelperErrorWrapper):
            return stream.raiseError()
        srcStream = self.__getStream(srcStreamName)
        if isinstance(srcStream, VcsHelperErrorWrapper):
            return srcStream.raiseError()
        if srcStream['Parent'] != stream['Stream']:
            error = VcsHelperError('p4', ErrorCategory.repo)
            error.raiseError(P4RepoErrorCode.stream_not_parent,
                parent=stream['Stream'], stream=srcStreamName)
        
        result = p4Run(self.p4, 'copy', **{
            '-Af': True,    # only stream copy
            '-S': srcStreamName
        })
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError(returnResult=None)
        
        streamHead = self.__getStreamHead(srcStreamName)
        defaultPending = self.getNewCommit(
                f'Copy {srcStreamName} at {streamHead.vcsData} up to'\
                f' {stream["Stream"]}.')
        if 'Files' not in defaultPending.commitRef:
            return None
        if commit is None:
            defaultPending.save()
            return defaultPending
        else:
            fileList = commit.commitRef.setdefault('Files', [])
            fileList.extend(defaultPending.commitRef['Files'])
            return commit

    @checkClient.__func__()
    def streamMergeDown(self, 
            commit: typing.Optional[Commit]=None) -> typing.Optional[Commit]:
        stream = self.__getStreamFromClient(self.client)
        if isinstance(stream, VcsHelperErrorWrapper):
            return stream.raiseError()
        if stream['Parent'] is None:
            error = VcsHelperError('p4', ErrorCategory.repo)
            error.raiseError(P4RepoErrorCode.stream_no_parent,
                                                stream=stream['Stream'])

        result = p4Run(self.p4, 'merge', **{
            '-Af': True,    # only stream copy
            '-r': True,     # merge direction
            '-S': stream['Stream']
        })
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError(returnResult=None)
        
        streamHead = self.__getStreamHead(stream["Parent"])
        defaultPending = self.getNewCommit(
                            f'Merge {stream["Parent"]} at {streamHead.vcsData}'\
                            f' down to {stream["Stream"]}.')
        if 'Files' not in defaultPending.commitRef:
            return None
        if commit is None:
            defaultPending.save()
            return defaultPending
        else:
            fileList = commit.commitRef.setdefault('Files', [])
            fileList.extend(defaultPending.commitRef['Files'])
            return commit

    @checkClient.__func__()
    def resolve(self, commit: typing.Optional[Commit]=None) -> int:
        options = {
            '-as': True,    # safe merge
        }
        if commit is not None and commit.vcsData != -1:
            options['-c'] = commit.vcsData
        
        result = p4Run(self.p4, 'resolve', **options)
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError()
        return result

    def cloneImpl(self, root: Path, force: bool,
            views: typing.List[str],
            clientName: typing.Optional[str]=None,
            stream: typing.Optional[str]=None,
            **kwargs):
        # verify root
        error = VcsHelperError('p4', ErrorCategory.repo)
        if root.exists():
            if not root.is_dir():
                return error.raiseError(P4RepoErrorCode.root_invalid,
                                                                    root=root)
            if not force:
                try:
                    root.unlink()
                except:
                    return error.raiseError(P4RepoErrorCode.root_not_empty,
                                                                    root=root)
        # create client
        if clientName is None:
            clientName = self.p4.client
        options = {}
        options.update(kwargs)
        options.update(Root=str(root), View=views)
        if stream is not None:
            options.update(Stream=stream)
        result = self.updateSpec('client', clientName, **options)
        if result != 0:
            return result

        self.p4.client = clientName
        return self.__updateClient()

    # implement abstract methods

    @property
    def submissionType(self) -> Repo.SubmissionType:
        return Repo.SubmissionType.submitPerSave

    @property
    def description(self) -> str:
        return self.__description

    # p4 version clone, just create a new client here
    # check cloneImpl for detail parameters
    def clone(self, root: Path, force: bool=False, **kwargs) -> int:
        return self.cloneImpl(root, force, **kwargs)

    @checkClient.__func__()
    def sync(self, commit: typing.Optional[Commit]=None,
            reset: bool=False) -> int:
        rootPath = getP4ValidLocalPath(self.root.joinpath('...'))
        if reset:
            result = self.clearPendings()
            if result != 0:
                return result

        if commit is not None:
            assert isinstance(commit, P4Commit)
            changelist = commit.vcsData
            fileSpec = rootPath + '@' + str(changelist)
        else:
            fileSpec = rootPath + '#head'

        result = p4Run(self.p4, 'sync', fileSpec)
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError()
        return 0

    @checkClient.__func__()
    def clearPendings(self) -> int:
       
        changeInfos = p4Run(self.p4, 'changes', **{
                '-s': 'pending',
                '-u': self.p4.user,
                '-c': self.p4.client,
        })
        if isinstance(changeInfos, VcsHelperErrorWrapper):
            return changeInfos.raiseError()

        rootPath = getP4ValidLocalPath(self.root.joinpath('...'))
        for changeInfo in changeInfos:
            # revert
            result = p4Run(self.p4, 'revert', rootPath,**{
                '-c': changeInfo['change'],
                '-w': True # delete added
            })
            if isinstance(result, VcsHelperErrorWrapper):
                return result.raiseError()

            # delete shelves
            if 'shelved' in changeInfo:
                result = p4Run(self.p4, 'shelve', **{
                    '-f': True, '-Af': True,
                    '-d': True,
                    '-c': changeInfo['change'],
                })
                if isinstance(result, VcsHelperErrorWrapper):
                    return result.raiseError()
            
            # delete changelist
            result = p4Run(self.p4, 'change', **{
                '-d': changeInfo['change'],
            })
            if isinstance(result, VcsHelperErrorWrapper):
                return result.raiseError()
            VcsHelperLogger.info(result[0])

        # default pending changelist
        result = p4Run(self.p4, 'revert', rootPath, **{
                '-w': True # delete added
            })
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError()

        return 0

    def getCommit(self, changelist: typing.Union[int, str]) -> typing.Optional[Commit]:
        change = p4Fetch(self.p4, 'change', changelist)
        if isinstance(change, VcsHelperErrorWrapper):
            return change.raiseError(returnResult=None)
        return P4Commit(self, change)

    @checkClient.__func__(exceptionOrExit=True)
    def getNewCommit(self, message: str) -> Commit:
        change = p4Fetch(self.p4, 'change')
        if isinstance(change, VcsHelperErrorWrapper):
            change.raiseError(exceptionOrExit=True)
        change['Description'] = message
        return P4Commit(self, change)

    @checkClient.__func__(exceptionOrExit=True)
    def getTopCommit(self) -> Commit:
        result = p4Run(self.p4, 'changes',
            getP4ValidLocalPath(self.root.joinpath('...')),
            **{
                '-s': 'submitted',
                '-m': 1,
            }
        )
        if isinstance(result, VcsHelperErrorWrapper):
            result.raiseError(exceptionOrExit=True)
        changelist = result[0]['change']
        return self.getCommit(changelist)

    def getCommitFromTag(self, tagName: str) -> typing.Optional[Commit]:
        label = p4Fetch(self.p4, 'label', tagName)
        if isinstance(label, VcsHelperErrorWrapper):
            return label.raiseError(returnResult=None)
        revision = label.get('Revision', None)
        if revision is None or revision[0] != '@':
            VcsHelperLogger.warning(f'Label {tagName} is not with changelist '\
                    'being set!')
            return None

        # only support single changelist label
        try:
            changelist = int(revision[1:])
        except:
            VcsHelperLogger.warning('Failed to extract changelist from Label '\
                f'{tagName}!\n\tLabel revision: {revision}')
            return None
        return self.getCommit(changelist)

    def setTag(self, tagName: str, commit: Commit, message: str) -> int:
        assert isinstance(commit, P4Commit)
        if commit.isWritable:
            error = VcsHelperError('p4', ErrorCategory.tag)
            return error.raiseError(P4RepoErrorCode.tag_to_pending)
        changelist = commit.vcsData

        # create or get label
        options = {
            'Owner': None,
        }
        options.update(
            Description=message,
            Options='locked noautoreload',
            Revision=f'@{changelist}',
            View=[],
        )
        result = p4Fetch(self.p4, 'client')
        if isinstance(result, VcsHelperErrorWrapper):
            return result.raiseError()
        for view in result['View']:
            depotPath = view.split(' ')[0]
            if depotPath[0] == '-':
                continue
            options['View'].append(depotPath)

        return self.updateSpec('label', tagName, **options)

    def deleteTag(self, tagName: str) -> int:
        return self.deleteSpec('label', tagName, True)

    def getTagMessage(self, tagName: str) -> typing.Optional[str]:
        label = p4Fetch(self.p4, 'label', tagName)
        if isinstance(label, VcsHelperErrorWrapper):
            return label.raiseError(returnResult=None)
        revision = label.get('Revision', None)
        if revision is None:
            VcsHelperLogger.warning(f'Label {tagName} is inexistent!')
            return None
        return label['Description']

    def iterCommits(self, after: typing.Optional[Commit] = None
            ) -> typing.Iterator[Commit]:
        self.lastIterResult = 0

        parameters = {
                '-s': 'submitted',
                '-r': True, # reversed
            }
        if after is not None:
            parameters['-e'] = after.vcsData + 1
        changes = p4Run(self.p4, 'changes',
            getP4ValidLocalPath(self.root.joinpath('...')), **parameters)
        if isinstance(changes, VcsHelperErrorWrapper):
            self.lastIterResult = changes.raiseError()
        for p4Change in changes:
            changelist = p4Change['change']
            commit = self.getCommit(changelist)
            yield commit

    @checkClient.__func__()
    def submit(self, commit: Commit) -> int:
        result = self.sync(self.getTopCommit())
        if result != 0:
            return result
        return commit.submit()
