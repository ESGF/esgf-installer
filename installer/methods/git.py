import logging
import os
import shutil

from plumbum import local
from plumbum import TEE
from plumbum.commands import ProcessExecutionError

from .distribution import FileManager
from ..utils import mkdir_p, pushd

class Git(FileManager):
    ''' Install file, git, and compressed components from a local or remote location '''
    def __init__(self, components):
        FileManager.__init__(self, components)
        self.log = logging.getLogger(__name__)
        self.git = local["git"]
        self.clone_args = ["clone", "--depth", "1"]
        self.version_args = ["log", "-1", '--format="%h %cd"']

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

    def _uninstall(self):
        FileManager._uninstall(self)

    def _versions(self):
        versions = {}
        for component in self.components:
            if not os.path.isdir(component["dest"]):
                versions[component["name"]] = None
                continue

            with pushd(component["dest"]):
                try:
                    result = self.git.run(self.version_args)
                except ProcessExecutionError:
                    versions[component["name"]] = "1"
                else:
                    versions[component["name"]] = result[1]

        return versions