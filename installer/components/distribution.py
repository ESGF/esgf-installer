import grp
import pwd

from ..utils import populate

class DistComponent(object):
    def __init__(self, config, name):
        config = config[name]
        # TODO Clean this up somehow
        replacements = {"name": name}
        try:
            replacements["version"] = config["version"]
        except KeyError:
            pass
        self.url = populate(config["url"], replacements)
        try:
            self.tar_root_dir = populate(config["tar_root_dir"], replacements)
        except KeyError:
            pass
        try:
            self.extract_dir = config["extract_dir"]
        except KeyError:
            pass
        try:
            self.local_dir = config["local_dir"]
        except KeyError:
            pass
        try:
            self.owner = config["owner"]
        except KeyError:
            pass
        else:
            if isinstance(self.owner, basestring):
                self.owner_uid = pwd.getpwnam(self.owner).pw_uid
                self.owner_gid = -1
            elif isinstance(self.owner, dict):
                self.owner_uid = pwd.getpwnam(self.owner["user"]).pw_uid
                self.owner_gid = grp.getgrnam(self.owner["group"]).gr_gid

    def version(self):
        pass
