from plumbum import local
from plumbum import TEE
import os

class Method(object):
    def __init__(self, components):
        self.components = [component() for component in components]

class PackageManager(Method):
    def __init__(self, components):
        Method.__init__(self, components)
        self.installers = {
            "yum": {
                "install_y": ["install", "-y"]
            },
            "apt": {
                "install_y": ["install", "-y"]
            }
        }
        self.managers = {
            "rpm": {
                "version": ["-q", "--queryformat", "%{VERSION}"]
            }
        }
        self.installer = local.get(*self.installers.keys())
        self.installer_name = os.path.basename(str(self.installer))
        self.manager = local.get(*self.managers.keys())
        self.manager_name = os.path.basename(str(self.manager))

    def install(self):
        # for component in self.components:
        #     component.pre_install()

        pkg_list = [component.pkg_names[self.installer_name] for component in self.components]
        args = self.installers[self.installer_name]["install_y"] + pkg_list
        result = self.installer.__getitem__(args) & TEE

        # for component in self.components:
        #     component.post_install()

    def versions(self):
        for component in self.components:
            args = self.managers[self.manager_name]["version"] + component.pkg_names[self.installer_name]
            result = self.manager.__getitem__(args) & TEE

class Mirror(Method):
    def __init__(self, components):
        Method.__init__(self, components)
