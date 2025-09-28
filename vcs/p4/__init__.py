from ..logger import *
VcsHelperError.registerVcs('p4', 1)
VcsHelperError.registerError('p4', ErrorCategory.ungrouped,
                                    1, VcsHelperError.ErrorLevel.fatal,
                                    'Fatal: P4Python is not installed!')

try:
    import P4
except ImportError:
    error = VcsHelperError('p4', ErrorCategory.ungrouped)
    error.raiseError(1)

#from . import p4_runner
#
#__all__ = [
#    'P4Repo',
#]
#__all__ += p4_runner.__all__
#
#from .p4_runner import *
#from .p4_repo import P4Repo
