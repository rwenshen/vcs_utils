from ..common.logger import *
VcsHelperError.registerVcs('git', 2)
VcsHelperError.registerError('git', ErrorCategory.ungrouped, 1,
                                        'Fatal: GitPython is not installed!')
try:
    import git
except ImportError:
    error = VcsHelperError('git', ErrorCategory.ungrouped)
    VcsHelperError.raiseType = VcsHelperError.RaiseType.exit_code
    error.raiseError(1, exceptionOrExit=True)

__all__ = [
    'GitRepo',
]

from .git_repo import GitRepo
