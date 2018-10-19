'''Constant values which are used by the installer to properly communicate'''

import os.path as path

OK = 1
NOT_INSTALLED = 2
BAD_VERSION = 3
INFO_FILE = path.join(path.dirname(__file__), ".info")
UNIQUE_KEY = "unique_key"
LIST_KEYWORD = "list_keyword"
LIST_KEY_SCHEME = "{key}"+LIST_KEYWORD+"{index}"
