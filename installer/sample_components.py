from string import Formatter

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
