''' Common methods for performing installations '''
import os

from plumbum import local
from plumbum import TEE
from plumbum.commands import ProcessExecutionError

from .generic import Generic

class PackageManager(Generic):
    ''' System package managers, does not include pip (could it though?) '''
    def __init__(self, components, component_config):
        Generic.__init__(self, components, component_config)
        # Installer interface for different OS's
        self.installers = {
            "yum": {
                "install_y": ["install", "-y"],
                "name_scheme": '"{name}-{version}"'
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
                result = self.query.__getitem__(args) & TEE
            except ProcessExecutionError:
                versions[component.name] = None
            else:
                versions[component.name] = str(result[1]).strip()
        return versions

class Pip(Generic):
    ''' Install components using the pip command line tool '''
    def __init__(self, components, component_config):
        Generic.__init__(self, components, component_config)

    def _install(self, names):
        pass

    def _versions(self):
        return {}
