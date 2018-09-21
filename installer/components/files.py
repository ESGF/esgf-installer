import grp
import pwd

from ..utils import populate
from ..utils import populated
from ..utils import check_populatable

class FileComponent(object):
    def __init__(self, name, config):
        self.name = name
        # TODO Clean this up somehow
        replacements = {"name": name}
        for param in config:
            if not isinstance(config[param], basestring):
                continue
            check_populatable(param, config[param], config.keys()+replacements.keys())
        all_populated = False
        while not all_populated:
            all_populated = True
            for param in config:
                if not isinstance(config[param], basestring):
                    continue
                if param in replacements:
                    continue
                if populated(config[param]):
                    replacements[param] = config[param]
                else:
                    config[param] = populate(config[param], replacements)
                    all_populated = False
        self.source = config["source"]
        self.dest = config["dest"]
        try:
            self.extract = config["extract"]
        except KeyError:
            pass
        try:
            self.tar_root_dir = config["tar_root_dir"]
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
