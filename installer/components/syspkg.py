import logging

from .generic import GenericComponent
from ..utils import populate

class SysPkgComponent(GenericComponent):
    def __init__(self, name, config):
        self.log = logging.getLogger(__name__)
        GenericComponent.__init__(self, name, config)
        try:
            self.req_version = self.config["version"]
        except KeyError:
            pass
        try:
            self.pkg_names = self.config["pkg_names"]
        except KeyError:
            pass
        else:
            for pkg_tool in self.pkg_names:
                self.pkg_names[pkg_tool] = populate(self.pkg_names[pkg_tool], self.replacements)
