from enum import Enum, auto
import typing
import functools
from pathlib import Path
from P4 import P4, P4Exception

from .._common.logger import *
from .._common.commit import CommitErrorCode


__all__ = [
    'getP4ValidLocalPath',
    'getLocalPathFromP4',
    'p4Run',
    'p4Fetch',
    'p4Save',
    'verifyP4RunResultInt',
    'verifyP4RunResultDict',
    'verifyP4RunResultList',
    'verifyP4FetchResultDict',
]


class P4RunErrorCode(Enum):
    # ErrorCategory.remote
    sync = 1
    changelists = auto()
    submit = auto()

    fetch_changelist = 0x80
    fetch_user = auto()
    fetch_client = auto()
    fetch_stream = auto()
    fetch_job = auto()
    fetch_depot = auto()

    save_changelist = 0xa0
    save_user = auto()
    save_client = auto()
    save_stream = auto()
    save_job = auto()
    save_depot = auto()

    remote_error_last = auto()

    # ErrorCategory.commit
    add = CommitErrorCode.last.value
    edit = auto()
    delete = auto()
    move = auto()
    revert = auto()
    shelve = auto()
    unshelve = auto()
    copy = auto()
    merge = auto()
    resolve = auto()

    commit_error_last = auto()

    # ErrorCategory.file_stat
    info = 2000
    where = auto()
    fstat = auto()
    opened = auto()
    describe = auto()

    file_stat_last = auto()

    # ErrorCategory.tag
    fetch_label = 3000
    save_label = auto()

    tag_last = auto()

    # ungrouped
    unexpected_results = 0xfffe
    ungrouped_error = 0xffff

VcsHelperError.registerError('p4',
    ErrorCategory.ungrouped, P4RunErrorCode.unexpected_results,
    'Unexpect p4 run result {results}!')
VcsHelperError.registerError('p4',
    ErrorCategory.ungrouped, P4RunErrorCode.ungrouped_error,
    '{error}')

VcsHelperError.registerError('p4',
    ErrorCategory.remote, P4RunErrorCode.sync,
    'Failed to sync!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.remote, P4RunErrorCode.changelists,
    'Failed to query changelists!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.remote, P4RunErrorCode.submit,
    'Failed to submit changelists!\n{error}')

VcsHelperError.registerError('p4',
    ErrorCategory.remote, P4RunErrorCode.fetch_changelist,
    'Failed to fetch changelists!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.remote, P4RunErrorCode.fetch_user,
    'Failed to fetch user!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.remote, P4RunErrorCode.fetch_client,
    'Failed to fetch client!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.remote, P4RunErrorCode.fetch_stream,
    'Failed to fetch stream!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.remote, P4RunErrorCode.fetch_job,
    'Failed to fetch job!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.remote, P4RunErrorCode.fetch_depot,
    'Failed to fetch depot!\n{error}')

VcsHelperError.registerError('p4',
    ErrorCategory.remote, P4RunErrorCode.save_changelist,
    'Failed to save changelists!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.remote, P4RunErrorCode.save_user,
    'Failed to save user!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.remote, P4RunErrorCode.save_client,
    'Failed to save client!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.remote, P4RunErrorCode.save_stream,
    'Failed to save stream!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.remote, P4RunErrorCode.save_job,
    'Failed to save job!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.remote, P4RunErrorCode.save_depot,
    'Failed to save depot!\n{error}')

VcsHelperError.registerError('p4',
    ErrorCategory.commit, P4RunErrorCode.add,
    'Failed to add!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.commit, P4RunErrorCode.edit,
    'Failed to open for edit!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.commit, P4RunErrorCode.delete,
    'Failed to delete!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.commit, P4RunErrorCode.move,
    'Failed to move!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.commit, P4RunErrorCode.revert,
    'Failed to revert!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.commit, P4RunErrorCode.shelve,
    'Failed to shelve!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.commit, P4RunErrorCode.unshelve,
    'Failed to un-shelve!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.commit, P4RunErrorCode.copy,
    'Failed to copy!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.commit, P4RunErrorCode.merge,
    'Failed to merge!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.commit, P4RunErrorCode.resolve,
    'Failed to resolve!\n{error}')

VcsHelperError.registerError('p4',
    ErrorCategory.file_stat, P4RunErrorCode.info,
    'Failed to query p4 info!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.file_stat, P4RunErrorCode.where,
    'Failed to query where!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.file_stat, P4RunErrorCode.fstat,
    'Failed to query fstat!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.file_stat, P4RunErrorCode.opened,
    'Failed to query opened!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.file_stat, P4RunErrorCode.describe,
    'Failed to describe changelist!\n{error}')

VcsHelperError.registerError('p4',
    ErrorCategory.tag, P4RunErrorCode.fetch_label,
    'Failed to fetch label!\n{error}')
VcsHelperError.registerError('p4',
    ErrorCategory.tag, P4RunErrorCode.save_label,
    'Failed to save label!\n{error}')


def __processP4RunResultsDefault(results) -> typing.List[typing.Dict]:
    return results

def __processP4Exception(e: Exception|P4Exception|str,
        errorCategory: ErrorCategory=ErrorCategory.ungrouped,
        errorCode: int|Enum = 0) -> int|VcsHelperErrorWrapper:
    if isinstance(e, P4Exception):
        p4Exception: P4Exception = e
        if isinstance(p4Exception.warnings, (list, tuple)):
            warnings: typing.Iterable[str] = p4Exception.warnings # type: ignore
            for warning in warnings:
                VcsHelperLogger.warning(warning)
        if isinstance(p4Exception.warnings, (list, tuple)):
            errors: typing.Sized[str] = p4Exception.errors # type: ignore
            if len(errors) == 0:
                return 0
        errorWrapper = VcsHelperErrorWrapper(
            'p4', errorCategory, errorCode, error=e)
    else:
        errorMsg: str = ''
        if isinstance(e, Exception):
            errorMsg = f'Unexpected error in p4Run: {e}'
        elif isinstance(e, str):
            errorMsg = e
        errorWrapper = VcsHelperErrorWrapper('p4', ErrorCategory.ungrouped,
                                P4RunErrorCode.ungrouped_error, error=errorMsg)
    return errorWrapper

def __processP4FileOperationResults(results, format: str) -> int:
    for result in results:
        if isinstance(result, str):
            VcsHelperLogger.info('\t' + result)
        else:
            VcsHelperLogger.info('\t' + format.format(**result))
    return 0

def __processP4SubmitResults(results) -> int:
    info = results[-1]
    if 'submittedChange' in info:
        changelist = info['submittedChange']
        VcsHelperLogger.info(f'\tChangelist {changelist} is submitted.')
        return int(changelist)
    assert False, 'Impossible'

def __processP4ResolveResults(results) -> int:
    index = 0
    while index < len(results):
        resolveInfo = results[index]
        index += 1
        resolveType = resolveInfo['resolveType']
        if resolveType == 'content':
            index += 1  # for diff info
        elif resolveType in ['branch', 'delete', 'move']:
            pass
        else:
            assert 0, 'TODO'
        result = results[index]
        index += 1
        if isinstance(result, dict):
            fileName = resolveInfo['clientFile']
            VcsHelperLogger.info(f'\t"{fileName}" has been resolved.')
        else:
            VcsHelperLogger.info('\t' + result)
    return 0

__p4RunResultsProcessors = {
    'sync': functools.partial(__processP4FileOperationResults,
                            format='"{depotFile}" was synced.'),
    'add': functools.partial(__processP4FileOperationResults,
                            format='"{depotFile}" was added.'),
    'edit': functools.partial(__processP4FileOperationResults,
                            format='"{depotFile}" was opened for edit.'),
    'delete': functools.partial(__processP4FileOperationResults,
                            format='"{depotFile}" was deleted.'),
    'move': functools.partial(__processP4FileOperationResults,
                            format='"{fromFile}" was moved to {depotFile}.'),
    'revert': functools.partial(__processP4FileOperationResults,
                            format='"{depotFile}" was reverted.'),
    'shelve': functools.partial(__processP4FileOperationResults,
                            format='"{depotFile}" was shelved.'),
    'unshelve': functools.partial(__processP4FileOperationResults,
                            format='"{depotFile}" was un-shelved.'),
    'copy': functools.partial(__processP4FileOperationResults,
                            format='"{depotFile}" was copied with action '\
                                    '"{action}" from "{fromFile}".'),
    'merge': functools.partial(__processP4FileOperationResults,
                            format='"{depotFile}" was merged from "{fromFile}".'),
    'resolve': __processP4ResolveResults,
    'submit': __processP4SubmitResults,
}

__p4RunExceptionProcessors = {
    'sync': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.remote,
                    errorCode=P4RunErrorCode.sync),
    'add': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.commit,
                    errorCode=P4RunErrorCode.add),
    'edit': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.commit,
                    errorCode=P4RunErrorCode.edit),
    'delete': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.commit,
                    errorCode=P4RunErrorCode.delete),
    'move': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.commit,
                    errorCode=P4RunErrorCode.move),
    'revert': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.commit,
                    errorCode=P4RunErrorCode.revert),
    'shelve': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.commit,
                    errorCode=P4RunErrorCode.shelve),
    'unshelve': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.commit,
                    errorCode=P4RunErrorCode.unshelve),
    'copy': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.commit,
                    errorCode=P4RunErrorCode.copy),
    'merge': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.commit,
                    errorCode=P4RunErrorCode.merge),
    'resolve': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.commit,
                    errorCode=P4RunErrorCode.resolve),
    'changes': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.remote,
                    errorCode=P4RunErrorCode.changelists),
    'submit': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.remote,
                    errorCode=P4RunErrorCode.submit),
    'info': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.file_stat,
                    errorCode=P4RunErrorCode.info),
    'where': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.file_stat,
                    errorCode=P4RunErrorCode.where),
    'fstat': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.file_stat,
                    errorCode=P4RunErrorCode.fstat),
    'opened': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.file_stat,
                    errorCode=P4RunErrorCode.opened),
    'describe': functools.partial(__processP4Exception,
                    errorCategory=ErrorCategory.file_stat,
                    errorCode=P4RunErrorCode.describe),
}

def getP4ValidLocalPath(p: Path) -> str:
    file = str(p)
    file = file.replace('%', '%25')
    file = file.replace('@', '%40')
    file = file.replace('#', '%23')
    return file

def getLocalPathFromP4(p: Path) -> str:
    file = str(p)
    file = file.replace('%25', '%')
    file = file.replace('%40', '@')
    file = file.replace('%23', '#')
    return file

def p4Run(p4: P4, cmd: str, *fileSpecs, **kwargs):
    try:
        args = [cmd]
        for option, value in kwargs.items():
            args.append(str(option))
            if not isinstance(value, bool):
                args.append(str(value))
        for fileSpec in fileSpecs:
            args.append(str(fileSpec))

        results = p4.run(*args)
    except P4Exception as e:
        exceptionProcessFunc = __p4RunExceptionProcessors.get(cmd,
                                    functools.partial(__processP4Exception))
        return exceptionProcessFunc(e)
    except Exception as e:
        VcsHelperLogger.error(f'Unexpected error in p4Run: {e}')
        return VcsHelperErrorWrapper('p4', ErrorCategory.ungrouped,
                                    P4RunErrorCode.ungrouped_error, error=e)

    resultProcessFunc = __p4RunResultsProcessors.get(
                                    cmd, __processP4RunResultsDefault)
    return resultProcessFunc(results)

__p4FetchExceptionProcessors = {
    'change': functools.partial(__processP4Exception,
                        errorCategory=ErrorCategory.remote,
                        errorCode=P4RunErrorCode.fetch_changelist),
    'label': functools.partial(__processP4Exception,
                        errorCategory=ErrorCategory.tag,
                        errorCode=P4RunErrorCode.fetch_label),
    'user': functools.partial(__processP4Exception,
                        errorCategory=ErrorCategory.remote,
                        errorCode=P4RunErrorCode.fetch_user),
    'client': functools.partial(__processP4Exception,
                        errorCategory=ErrorCategory.remote,
                        errorCode=P4RunErrorCode.fetch_client),
    'stream': functools.partial(__processP4Exception,
                        errorCategory=ErrorCategory.remote,
                        errorCode=P4RunErrorCode.fetch_stream),
    'job': functools.partial(__processP4Exception,
                        errorCategory=ErrorCategory.remote,
                        errorCode=P4RunErrorCode.fetch_job),
    'depot': functools.partial(__processP4Exception,
                        errorCategory=ErrorCategory.remote,
                        errorCode=P4RunErrorCode.fetch_depot),
}

def p4Fetch(p4: P4, specType: str, name=None, **kwargs):
    try:
        args = []
        for option, value in kwargs.items():
            args.append(str(option))
            if not isinstance(value, bool):
                args.append(str(value))
        if name is not None:
            args.append(str(name))

        fetchFunc = getattr(p4, f'fetch_{specType}')
        return fetchFunc(*args)
    except Exception as e:
        exceptionProcessFunc = __p4FetchExceptionProcessors.get(specType,
                                    functools.partial(__processP4Exception))
        return exceptionProcessFunc(e)

__p4SaveExceptionProcessors = {
    'change': functools.partial(__processP4Exception,
                        errorCategory=ErrorCategory.remote,
                        errorCode=P4RunErrorCode.save_changelist),
    'label': functools.partial(__processP4Exception,
                        errorCategory=ErrorCategory.tag,
                        errorCode=P4RunErrorCode.save_label),
    'user': functools.partial(__processP4Exception,
                        errorCategory=ErrorCategory.remote,
                        errorCode=P4RunErrorCode.save_user),
    'client': functools.partial(__processP4Exception,
                        errorCategory=ErrorCategory.remote,
                        errorCode=P4RunErrorCode.save_client),
    'stream': functools.partial(__processP4Exception,
                        errorCategory=ErrorCategory.remote,
                        errorCode=P4RunErrorCode.save_stream),
    'job': functools.partial(__processP4Exception,
                        errorCategory=ErrorCategory.remote,
                        errorCode=P4RunErrorCode.save_job),
    'depot': functools.partial(__processP4Exception,
                        errorCategory=ErrorCategory.remote,
                        errorCode=P4RunErrorCode.save_depot),
}

def p4Save(p4: P4, specType: str, spec: dict, **kwargs):
    try:
        args = []
        for option, value in kwargs.items():
            args.append(option)
            if not isinstance(value, bool):
                args.append(value)
        args.append(spec)

        saveFunc = getattr(p4, f'save_{specType}')
        return saveFunc(*args)
    except Exception as e:
        exceptionProcessFunc = __p4SaveExceptionProcessors.get(specType,
                                    functools.partial(__processP4Exception))
        return exceptionProcessFunc(e)

def __raiseP4RunResultError(
        results: int|typing.List[typing.Dict]|VcsHelperErrorWrapper,
        **kwargs) -> int:
    if isinstance(results, VcsHelperErrorWrapper):
        return results.raiseError(**kwargs)
    else:
        error = VcsHelperError('p4', ErrorCategory.ungrouped)
        exceptionOrExit = kwargs.get('exceptionOrExit', False)
        return error.raiseError(P4RunErrorCode.unexpected_results,
                        exceptionOrExit=exceptionOrExit, results=results)

# return: (0, results) if results is int, else (errorCode, 0)
def verifyP4RunResultInt(
        results: int|typing.List[typing.Dict]|VcsHelperErrorWrapper,
        **kwargs) -> typing.Tuple[int, int]:
    if isinstance(results, int):
        return 0, results
    else:
        return __raiseP4RunResultError(results, **kwargs), 0

# return: (0, results) if results is list contains only one single dict
#                      else (errorCode, {})
def verifyP4RunResultDict(
        results: int|typing.List[typing.Dict]|VcsHelperErrorWrapper,
        **kwargs) -> typing.Tuple[int, typing.Dict]:
    if isinstance(results, list) and len(results) == 1:
        return 0, results[0]
    else:
        return __raiseP4RunResultError(results, **kwargs), {}

# return: (0, results) if results is list contains dicts, else (errorCode, [])
def verifyP4RunResultList(
        results: int|typing.List[typing.Dict]|VcsHelperErrorWrapper,
        **kwargs) -> typing.Tuple[int, typing.List[typing.Dict]]:
    if isinstance(results, list):
        return 0, results
    else:
        return __raiseP4RunResultError(results, **kwargs), []

# return: (0, results) if results is list contains only one single dict
#                      else (errorCode, {})
def verifyP4FetchResultDict(
        result: int|typing.Dict|VcsHelperErrorWrapper,
        **kwargs) -> typing.Tuple[int, typing.Dict]:
    if isinstance(result, dict):
        return 0, result
    else:
        return __raiseP4RunResultError(result, **kwargs), {}
