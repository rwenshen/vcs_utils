from ..logger import *
VcsErrorManager.registerVcs('git', 2)
VcsErrorManager.registerError('git', ErrorCategory.ungrouped,
    1, VcsErrorManager.ErrorLevel.fatal,
    'Fatal: GitPython is not installed!\n'\
        'You can run "pip install GitPython" to install it.')
__errorManager = VcsErrorManager('git', ErrorCategory.ungrouped)

# Check If GitPython is installed
try:
    import git
except ImportError:
    __errorManager.raiseError(1)

#__all__ = [
#    'GitRepo',
#]
#
#from .git_repo import GitRepo
