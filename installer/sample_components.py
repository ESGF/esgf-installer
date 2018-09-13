from string import Formatter
import pwd
import grp

class SysPkgComponent(object):
    def __init__(self, config, name):
        config = config[name]
        if isinstance(config, basestring):
            version = config
            if version != "latest":
                self.req_version = version
        elif isinstance(config, dict):
            try:
                self.req_version = config["version"]
            except KeyError:
                pass
            try:
                self.pkg_names = config["names"]
            except KeyError:
                pass
            else:
                for pkg_tool in self.pkg_names:
                    pkg_name = self.pkg_names[pkg_tool]
                    fieldnames = [fname for _, fname, _, _ in Formatter().parse(pkg_name) if fname]
                    if not fieldnames:
                        continue
                    replacements = {}
                    for field in fieldnames:
                        if field == "version":
                            replacements["version"] = self.req_version
                        elif field == "name":
                            replacements["name"] = name
                    if replacements:
                        self.pkg_names[pkg_tool] = pkg_name.format(**replacements)

class Ant(SysPkgComponent):
    def __init__(self, config):
        self.name = "ant"
        SysPkgComponent.__init__(self, config, self.name)

class DistComponent(object):
    def __init__(self, config, name):
        self.config = config[name]
        self.url = self.config["url"]
        try:
            self.extract_dir = self.config["extract_dir"]
        except KeyError:
            pass
        try:
            self.local_dir = self.config["local_dir"]
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


class Java(DistComponent):
    def __init__(self, config):
        self.name = "java"
        DistComponent.__init__(self, config, self.name)

class Thredds(DistComponent):
    def __init__(self, config):
        self.name = "thredds"
        DistComponent.__init__(self, config, self.name)
