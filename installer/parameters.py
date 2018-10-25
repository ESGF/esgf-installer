
import os
import os.path as path
import socket

_PARAMS = {
    "home": path.join(os.sep, "esg"),
    "env": path.join(os.sep, "etc", "esg.env"),
    "config": path.join("${home}", "config"),
    "mirror": "https://aims1.llnl.gov/esgf/dist",
    "proxy_name": socket.getfqdn()
}
_TRUST = {
    "tspass": "changeit",
    "kspass": "needtopromptuser"
}
PARAMS = {
    "ESGF_PARAMS" : _PARAMS,
    "TRUST_PARAMS":
}
