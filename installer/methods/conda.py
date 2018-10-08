import json
import os

from plumbum import local
from plumbum import TEE

from .generic import Generic

class Conda(Generic):
    ''' Install components using the pip command line tool '''
    def __init__(self, components):
        Generic.__init__(self, components)
        self.conda = local.get(os.environ["CONDA_EXE"])
        self.install_args = ["install", "-y"]
        self.uninstall_args = ["uninstall", "-y"]
        self.version_args = ["list", "--json"]

    def _install(self, names):
        conda_list = []
        channels = set()
        for component in self.components:
            if component["name"] not in names:
                continue
            try:
                for channel in component["channels"]:
                    channels.add(channel)
            except KeyError:
                pass
            try:
                conda_name = component["conda_name"]
            except KeyError:
                conda_name = component["name"]
            conda_list.append(conda_name)
        if conda_list:
            if channels:
                channel_args = []
                for channel in channels:
                    channel_args += ["-c", channel]
                args = self.install_args + conda_list + channel_args
            else:
                args = self.install_args + conda_list
            result = self.conda.__getitem__(args) & TEE

    def _uninstall(self):
        conda_list = [component["name"] for component in self.components]
        if conda_list:
            args = self.uninstall_args + conda_list
            result = self.conda.__getitem__(args) & TEE

    def _versions(self):
        versions = {}
        result = self.conda.run(self.version_args)
        info = json.loads(result[1])
        for component in self.components:
            # Get the version with "name" matching pkg_name, if not present get None
            versions[component["name"]] = next(
                (pkg["version"] for pkg in info if pkg["name"].lower() == component["name"].lower()),
                None
            )
        return versions
