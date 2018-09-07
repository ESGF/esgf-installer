from plumbum import local

class Method(object):
    def __init__(self, components):
        self.components = [component() for component in components]

class PackageManager(Method):
    def __init__(self, components):
        Method.__init__(self, components)
        self.installer = local["yum"]
        self.manager = local["rpm"]

    def install(self):
        pkg_list = [component.pkg_names[self.installer] for component in self.components]
        args = ["install", "-y"] + pkg_list
        self.installer.__getitem__(args)

    def versions(self):
        pass
        #rpm -q pkg_name --queryformat "%{VERSION}"

class Mirror(Method):
    def __init__(self, components):
        pass
