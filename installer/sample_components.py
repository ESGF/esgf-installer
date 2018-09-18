import pwd
import grp

from .utils import populate

class SysPkgComponent(object):
    def __init__(self, config, name):
        config = config[name]
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
                self.pkg_names = config["names"]
            except KeyError:
                pass
            else:
                for pkg_tool in self.pkg_names:
                    self.pkg_names[pkg_tool] = populate(self.pkg_names[pkg_tool], replacements)

class Ant(SysPkgComponent):
    def __init__(self, config):
        self.name = "ant"
        SysPkgComponent.__init__(self, config, self.name)

class Postgres(SysPkgComponent):
    def __init__(self, config):
        self.name = "postgres"
        SysPkgComponent.__init__(self, config, self.name)

class DistComponent(object):
    def __init__(self, config, name):
        config = config[name]
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

class Java(DistComponent):
    def __init__(self, config):
        self.name = "java"
        DistComponent.__init__(self, config, self.name)



class Thredds(DistComponent):
    def __init__(self, config):
        self.name = "thredds"
        DistComponent.__init__(self, config, self.name)

class Tomcat(DistComponent):
    def __init__(self, config):
        self.name = "tomcat"
        DistComponent.__init__(self, config, self.name)
