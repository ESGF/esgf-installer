
import os
import os.path as path

_PARAMS = {
    "home": path.join(os.sep, "esg"),
    "env": path.join(os.sep, "etc", "esg.env"),
    "config": path.join("${esgf_home}", "config"),
    "mirror": "http://aims1.llnl.gov/esgf/dist"
}

ESGF_PARAMS = {
    "ESGF_PARAMS" : _PARAMS
}
