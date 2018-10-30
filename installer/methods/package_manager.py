''' Common methods for performing installations '''
import json
import logging
import os
import os.path as path

from plumbum import local
from plumbum import TEE
from plumbum.commands import ProcessExecutionError

from .generic import Generic
from .conda import Conda


class PackageManager(Generic):
    ''' System package managers, does not include pip (could it though?) '''
    def __init__(self, components):
        Generic.__init__(self, components)
        self.log = logging.getLogger(__name__)
        # Installer interface for different OS's
        self.installers = {
            "yum": {
                "install_y": ["install", "-y"],
                "name_scheme": '"{name}-{version}"',
                "uninstall": ["remove", "-y"]
            },
            "apt": {
                "install_y": ["install", "-y"],
                "name_scheme": '"{name}-{version}"'
            }
        }
        # Ways of querying for version/existence
        # repoquery --show-dupes --qf="%{name}:%{version}" postgresql ant tomcat httpd
        self.queries = {
            "rpm": {
                "version": ["-q", "--queryformat", "%{VERSION}"]
            },
            "dpkg-query": {
                "version": ["--show", "--showformat=${Version}"]
            }
        }
        # Find what is available to be used
        self.installer = local.get(*self.installers.keys())
        self.installer_name = os.path.basename(str(self.installer))
        self.query = local.get(*self.queries.keys())
        self.query_name = os.path.basename(str(self.query))

    def _install(self, names):
        ''' A realization of an install process '''
        pkg_list = []
        for component in self.components:
            if component["name"] not in names:
                continue
            try:
                version = component["version"]
            except KeyError:
                version = None
            try:
                pkg_name = component[self.installer_name]
            except KeyError:
                scheme = self.installers[self.installer_name]["name_scheme"]
                if version is not None:
                    pkg_name = scheme.format(name=component["name"], version=version)
                else:
                    pkg_name = component["name"]
            pkg_list.append(pkg_name)
        if pkg_list:
            args = self.installers[self.installer_name]["install_y"] + pkg_list
            result = self.installer.__getitem__(args) & TEE

    def _versions(self):
        ''' A realization of a version fetching process '''
        versions = {}
        for component in self.components:
            try:
                pkg_name = component[self.installer_name]
            except KeyError:
                pkg_name = component["name"]
            args = self.queries[self.query_name]["version"] + [pkg_name]
            try:
                result = self.query.run(args)
            except ProcessExecutionError:
                versions[component["name"]] = None
            else:
                versions[component["name"]] = str(result[1]).strip()
        return versions

    def _uninstall(self):
        pkg_list = []
        for component in self.components:
            try:
                version = component["version"]
            except KeyError:
                version = None
            try:
                pkg_name = component[self.installer_name]
            except KeyError:
                scheme = self.installers[self.installer_name]["name_scheme"]
                if version is not None:
                    pkg_name = scheme.format(name=component["name"], version=version)
                else:
                    pkg_name = component["name"]
            pkg_list.append(pkg_name)
        if pkg_list:
            args = self.installers[self.installer_name]["uninstall"] + pkg_list
            result = self.installer.__getitem__(args) & TEE


class Pip(Conda):
    ''' Install components using the pip command line tool '''
    def __init__(self, components):
        Conda.__init__(self, components)
        self.log = logging.getLogger(__name__)

        self.pip = local.get("pip")
        self.install_cmd = ["install"]
        self.uninstall_cmd = ["uninstall", "-y"]
        self.version_cmd = ["list", "--format=json"]
        self.run_in_env = local.get(path.join(path.dirname(__file__), "run_in_env.sh"))

    def _install(self, names):
        envs = {}
        for component in self.components:
            if component["name"] not in names:
                continue
            try:
                env = component["conda_env"]
            except KeyError:
                env = self.installer_env
            if env not in envs:
                envs[env] = {
                    "pip_list": []
                }
            try:
                pip_name = component["pip_name"]
            except KeyError:
                pip_name = component["name"]
            envs[env]["pip_list"].append(pip_name)
        for env in envs:
            if self._get_env(env) is None:
                self._create_env_w_pip(env)
            pip_list = envs[env]["pip_list"]
            args = [env, "pip"] + self.install_cmd + pip_list
            result = self.run_in_env.__getitem__(args) & TEE

    def _create_env_w_pip(self, env):
        self._create_env(env, ["pip", "python<3"], [])
        upgrade_args = [env, "pip", "install", "--upgrade", "pip"]
        result = self.run_in_env.__getitem__(upgrade_args) & TEE

    def _versions(self):
        versions = {}
        envs = {}
        for component in self.components:
            try:
                env = component["conda_env"]
            except KeyError:
                env = self.installer_env
            if env not in envs:
                envs[env] = {
                    "pip_list": []
                }
            envs[env]["pip_list"].append(component)

        for env in envs:
            if self._get_env(env) is None:
                for component in envs[env]["pip_list"]:
                    versions[component["name"]] = None
                continue
            args = [env, "pip"] + self.version_cmd
            result = self.run_in_env.run(args)
            info = json.loads(result[1])
            for component in envs[env]["pip_list"]:
                # Get the dictionary with "name" matching pkg_name, if not present get None
                versions[component["name"]] = next(
                    (pkg["version"] for pkg in info if pkg["name"].lower() == component["name"].lower()),
                    None
                )
        return versions

    def _uninstall(self):
        envs = {}
        for component in self.components:
            try:
                env = component["conda_env"]
            except KeyError:
                env = self.installer_env
            if env not in envs:
                envs[env] = {
                    "pip_list": []
                }
            envs[env]["pip_list"].append(component["name"])
        for env in envs:
            args = [env, "pip"] + self.uninstall_cmd + envs[env]["pip_list"]
            result = self.run_in_env.__getitem__(args) & TEE
