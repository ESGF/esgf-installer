import logging

from ..utils import populate

class SysPkgComponent(object):
    def __init__(self, name, config):
        self.log = logging.getLogger(__name__)
        self.name = name
        replacements = {"name": name}
        if isinstance(config, basestring):
            version = config
            if version != "latest":
                self.req_version = version
        elif isinstance(config, dict):
            try:
                self.req_version = config["version"]
                replacements["version"] = config["version"]
            except KeyError:
                pass
            try:
                self.pkg_names = config["pkg_names"]
            except KeyError:
                pass
            else:
                for pkg_tool in self.pkg_names:
                    self.pkg_names[pkg_tool] = populate(self.pkg_names[pkg_tool], replacements)
