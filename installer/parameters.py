
import os
import os.path as path

_PARAMS = {
    "home": path.join(os.sep, "esg"),
    "env": path.join(os.sep, "etc", "esg.env"),
    "config": path.join("${home}", "config"),
    "mirror": "https://aims1.llnl.gov/esgf/dist"
}

PARAMS = {
    "ESGF_PARAMS" : _PARAMS
}
