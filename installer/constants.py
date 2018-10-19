'''Constant values which are used by the installer to properly communicate'''

import os.path as path

OK = 1
NOT_INSTALLED = 2
BAD_VERSION = 3
INFO_FILE = _FILE_DIR = path.join(path.dirname(__file__), ".info")
UNIQUE_KEY = "UNIQUE_KEY"
