
from plumbum import local
from plumbum import TEE

from .package_manager import Pip
from .distribution import FileManager

class EasyInstall(Pip, FileManager):
    def __init__(self, components):
        Pip.__init__(self, components)
        FileManager.__init__(self, components)
        self.easy_install = local["easy_install"]

    def _install(self, names):
        FileManager._install(self, names)
        for component in self.components:
            if component["name"] not in names:
                continue
            args = [component["dest"]]
            result = self.easy_install.__getitem__(args) & TEE

    def _uninstall(self):
        Pip._uninstall(self)

    def _versions(self):
        return Pip._versions(self)
