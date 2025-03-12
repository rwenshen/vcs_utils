from ..common.logger import *
VcsHelperError.registerVcs('p4', 1)
VcsHelperError.registerError('p4', ErrorCategory.ungrouped, 1,
                                        'Fatal: P4Python is not installed!')

try:
    import P4
except ImportError:
    error = VcsHelperError('p4', ErrorCategory.ungrouped)
    errorCode = error.raiseError(1)
    exit(errorCode)

from . import p4_runner

__all__ = [
    'P4Repo',
]
__all__ += p4_runner.__all__

from .p4_runner import *
from .p4_repo import P4Repo
