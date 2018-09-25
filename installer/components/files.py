import grp
import logging
import pwd

from .generic import GenericComponent

class FileComponent(GenericComponent):
    def __init__(self, name, config):
        self.log = logging.getLogger(__name__)
        GenericComponent.__init__(self, name, config)
        self.source = self.config["source"]
        self.dest = self.config["dest"]
        try:
            self.extract = self.config["extract"]
        except KeyError:
            pass
        try:
            self.tar_root_dir = self.config["tar_root_dir"]
        except KeyError:
            pass
        try:
            self.tag = self.config["tag"]
        except KeyError:
            pass
        try:
            self.owner = self.config["owner"]
        except KeyError:
            pass
        else:
            if isinstance(self.owner, basestring):
                self.owner_uid = pwd.getpwnam(self.owner).pw_uid
                self.owner_gid = -1
            elif isinstance(self.owner, dict):
                self.owner_uid = pwd.getpwnam(self.owner["user"]).pw_uid
                self.owner_gid = grp.getgrnam(self.owner["group"]).gr_gid
