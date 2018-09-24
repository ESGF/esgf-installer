''' Common methods for performing installations '''
import json
import logging
import os

from plumbum import local
from plumbum import TEE
from plumbum.commands import ProcessExecutionError

from .generic import Generic

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
                "uninstall": ["erase", "-y"]
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
            if component.name not in names:
                continue
            try:
                version = component.req_version
            except AttributeError:
                version = None
            try:
                pkg_name = component.pkg_names[self.installer_name]
            except AttributeError:
                scheme = self.installers[self.installer_name]["name_scheme"]
                if version is not None:
                    pkg_name = scheme.format(name=component.name, version=version)
                else:
                    pkg_name = component.name
            pkg_list.append(pkg_name)
        if pkg_list:
            args = self.installers[self.installer_name]["install_y"] + pkg_list
            result = self.installer.__getitem__(args) & TEE

    def _versions(self):
        ''' A realization of a version fetching process '''
        versions = {}
        for component in self.components:
            try:
                pkg_name = component.pkg_names[self.installer_name]
            except AttributeError:
                pkg_name = component.name
            args = self.queries[self.query_name]["version"] + [pkg_name]
            try:
                result = self.query.run(args)
            except ProcessExecutionError:
                versions[component.name] = None
            else:
                versions[component.name] = str(result[1]).strip()
        return versions

    def _uninstall(self):
        pkg_list = []
        for component in self.components:
            try:
                version = component.req_version
            except AttributeError:
                version = None
            try:
                pkg_name = component.pkg_names[self.installer_name]
            except AttributeError:
                scheme = self.installers[self.installer_name]["name_scheme"]
                if version is not None:
                    pkg_name = scheme.format(name=component.name, version=version)
                else:
                    pkg_name = component.name
            pkg_list.append(pkg_name)
        if pkg_list:
            args = self.installers[self.installer_name]["uninstall"] + pkg_list
            result = self.installer.__getitem__(args) & TEE

class Pip(Generic):
    ''' Install components using the pip command line tool '''
    def __init__(self, components):
        Generic.__init__(self, components)
        self.pip = local.get("pip")
        self.install_cmd = ["install"]
        self.uninstall_cmd = ["uninstall", "-y"]
        self.version_cmd = ["list", "--format=json"]

    def _install(self, names):
        pip_list = []
        for component in self.components:
            if component.name not in names:
                continue
            try:
                pip_name = component.pip_name
            except AttributeError:
                pip_name = component.name
            pip_list.append(pip_name)
        if pip_list:
            args = self.install_cmd + pip_list
            result = self.pip.__getitem__(args) & TEE

    def _versions(self):
        versions = {}
        args = self.version_cmd
        result = self.pip.run(args)
        info = json.loads(result[1])
        for component in self.components:
            # Get the dictionary with "name" matching pkg_name, if not present get None
            pkg = next((pkg for pkg in info if pkg["name"] == component.name), None)
            if pkg is None:
                versions[component.name] = None
            else:
                versions[component.name] = str(pkg['version'])
        return versions

    def _uninstall(self):
        pip_list = []
        for component in self.components:
            pip_list.append(component.name)
        if pip_list:
            args = self.uninstall_cmd + pip_list
            result = self.pip.__getitem__(args) & TEE
