import logging
import os
import shutil

from plumbum import local
from plumbum import TEE

from .distribution import FileManager
from ..utils import mkdir_p

class Git(FileManager):
    ''' Install file, git, and compressed components from a local or remote location '''
    def __init__(self, components):
        FileManager.__init__(self, components)
        self.log = logging.getLogger(__name__)
        self.git = local["git"]
        self.clone_args = ["clone", "--depth", "1"]

    def _install(self, names):
        for component in self.components:
            if component["name"] not in names:
                continue
            args = []
            args += self.clone_args
            try:
                args += ["--branch", component["tag"]]
            except KeyError:
                pass

            if os.path.isdir(component["dest"]):
                shutil.rmtree(component["dest"])

            dest_dir = os.path.dirname(component["dest"].rstrip(os.sep))
            mkdir_p(dest_dir)

            args += [component["source"], component["dest"]]
            result = self.git.__getitem__(args) & TEE

            FileManager._chown(self, component, component["dest"])
