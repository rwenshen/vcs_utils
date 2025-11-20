from ..logger import *
VcsErrorManager.registerVcs('p4', 1)
VcsErrorManager.registerError('p4', ErrorCategory.ungrouped,
    1, VcsErrorManager.ErrorLevel.fatal,
    'Fatal: P4Python is not installed!\n'\
        'You can run "pip install P4Python" to install it.')
VcsErrorManager.registerError('p4', ErrorCategory.ungrouped,
    2, VcsErrorManager.ErrorLevel.fatal,
    'Fatal: P4Python is not installed!')
__errorManager = VcsErrorManager('p4', ErrorCategory.ungrouped)

# Check If P4Python is installed and its version
try:
    import P4
except ImportError:
    __errorManager.raiseError(1)

# Check P4Python version, at least 2022.1 (for Python 3.10+ support)
import re
p4pythonVersionPattern = re.compile(r'(\d{4})\.(\d+)/(\d+)')
match = p4pythonVersionPattern.search(P4.P4.identify())
if not match:
    __errorManager.raiseError(1)
else:
    year, month, changelist = map(int, match.groups())
    if (year < 2022) or (year == 2022 and month < 1):
        __errorManager.raiseError(2)

#from . import p4_runner
#
#__all__ = [
#    'P4Repo',
#]
#__all__ += p4_runner.__all__
#
#from .p4_runner import *
#from .p4_repo import P4Repo
