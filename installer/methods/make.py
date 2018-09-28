
from plumbum import local
from plumbum import TEE

from .distribution import FileManager
from ..utils import pushd

class Make(FileManager):
    def __init__(self, components):
        FileManager.__init__(self, components)
        self.make = local["make"]
        self.install_arg = ["install"]

    def _install(self, names):
        FileManager._install(self, names)
        for component in self.components:
            if component.name not in names:
                continue
            with pushd(component.make_dir):
                self.make.run_tee()
                self.make.__getitem__(self.install_arg) & TEE
