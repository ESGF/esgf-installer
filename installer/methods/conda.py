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
        self.create_args = ["create", "-y"]
        self.uninstall_args = ["uninstall", "-y"]
        self.version_args = ["list", "--json"]
        self.installer_env = os.path.basename(os.environ["CONDA_PREFIX"])

    def _get_env(self, name):
        args = ["env", "list", "--json"]
        result = self.conda.run(args)
        env_info = json.loads(result[1])
        for env in env_info["envs"]:
            env_name = os.path.basename(env)
            if env_name == name:
                return name
        return None

    def _create_env(self, name, pkgs, channels):
        args = self.create_args + ["-n", name] + pkgs + channels
        result = self.conda.__getitem__(args) & TEE

    def _install(self, names):
        envs = {}
        for component in self.components:
            if component["name"] not in names:
                continue
            try:
                env = component["env"]
            except KeyError:
                env = self.installer_env
            if env not in envs:
                envs[env] = {
                    "channels": set(),
                    "conda_list": []
                }
            try:
                channels = set()
                for channel in component["channels"]:
                    envs[env]["channels"].add(channel)
            except KeyError:
                pass
            try:
                conda_name = component["conda_name"]
            except KeyError:
                conda_name = component["name"]
            envs[env]["conda_list"].append(conda_name)

        for env in envs:
            conda_list = envs[env]["conda_list"]
            channels = envs[env]["channels"]
            channel_args = []
            for channel in channels:
                channel_args += ["-c", channel]
            if self._get_env(env) is None:
                self._create_env(env, conda_list + ["python<3"], channel_args)
                continue

            args = self.install_args + ["-n", env] + conda_list + ["python<3"] + channel_args
            result = self.conda.__getitem__(args) & TEE


    def _uninstall(self):
        envs = {}
        for component in self.components:
            try:
                env = component["env"]
            except KeyError:
                env = self.installer_env
            try:
                envs[env].append(component["name"])
            except KeyError:
                envs[env] = [component["name"]]
        for env in envs:
            conda_list = envs[env]
            if self._get_env(env) is None:
                continue
            args = self.uninstall_args + ["-n", env] + conda_list
            result = self.conda.__getitem__(args) & TEE

    def _versions(self):
        versions = {}
        envs = {}
        for component in self.components:
            try:
                env = component["env"]
            except KeyError:
                env = self.installer_env
            try:
                envs[env].append(component)
            except KeyError:
                envs[env] = [component]
        print envs
        for env in envs:
            if self._get_env(env) is None:
                for component in envs[env]:
                    versions[component["name"]] = None
                continue
            args = self.version_args + ["-n", env]
            result = self.conda.run(args)
            info = json.loads(result[1])
            for component in envs[env]:
                # Get the version with "name" matching pkg_name, if not present get None
                versions[component["name"]] = next(
                    (pkg["version"] for pkg in info if pkg["name"].lower() == component["name"].lower()),
                    None
                )
        return versions
