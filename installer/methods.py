''' Common methods for performing installations within the ESGF stack '''
import os
from zipfile import Zipfile
from plumbum import local
from plumbum import TEE
import requests
from .install_codes import OK, NOT_INSTALLED, BAD_VERSION

class Generic(object):
    def __init__(self, components, component_config):
        self.components = [component(component_config) for component in components]

    def install(self):
        ''' Entry function to perform an installation '''
        self._pre_install()
        self._install()
        self._post_install()

    def _pre_install(self):
        ''' Allows for components to take actions before installation '''
        for component in self.components:
            try:
                component.pre_install()
            except AttributeError:
                continue

    def _install(self):
        ''' Generic version, should be reimplemented by children '''
        for component in self.components:
            component.install()

    def _post_install(self):
        ''' Allows for components to take actions after installation '''
        for component in self.components:
            try:
                component.post_install()
            except AttributeError:
                continue

    def statuses(self):
        ''' Entry function to get the statuses '''
        return self._statuses()

    def _statuses(self):
        ''' As long as versions is implemented correctly this is all that a status check is '''
        versions = self.versions()
        statuses = {}
        for component in self.components:
            name = component.name
            version = versions[name]
            if version is None:
                statuses[name] = NOT_INSTALLED
            else:
                try:
                    statuses[name] = OK if component.req_version == version else BAD_VERSION
                except AttributeError:
                    statuses[name] = OK
        return statuses

    def versions(self):
        ''' Entry function to get versions '''
        return self._versions()

    def _versions(self):
        ''' Generic version, should be reimplemented by children '''
        versions = {}
        for component in self.components:
            versions[component.name] = component.version()
        return versions

class DistributionArchive(Generic):
    ''' Install components from a URL '''
    def __init__(self, components, component_config):
        Generic.__init__(self, components, component_config)
        self.tmp = os.path.join(os.sep, "tmp")
        self.chunk_size = 1*1024

    def _install(self):
        for component in self.components:
            response = requests.get(component.url)
            remote_file = component.url.rsplit('/', 1)
            try:
                local_dir = component.local_dir
            except AttributeError:
                local_dir = self.tmp
            filename = os.path.join(local_dir, remote_file)
            #if not os.path.isfile(filename):
            with open(filename, 'wb') as localfile:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    localfile.write(chunk)
            try:
                extract_dir = component.extract_dir
            except AttributeError:
                pass
            else:
                #mkdir --p extract_dir
                with Zipfile(filename) as archive:
                    archive.extractall(extract_dir)

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

    def _install(self):
        ''' A realization of an install process '''
        pkg_list = []
        for component in self.components:
            try:
                version = component.req_version
            except AttributeError:
                version = "*"
            try:
                pkg_name = component.pkg_names[self.installer_name]
            except AttributeError:
                scheme = self.installers[self.installer_name]["name_scheme"]
                pkg_name = scheme.format(name=component.name, version=version)
            pkg_list.append(pkg_name)
        args = self.installers[self.installer_name]["install_y"] + pkg_list
        result = self.installer.__getitem__(args) & TEE

    def _versions(self):
        ''' A realization of a version fetching process '''
        versions = {}
        for component in self.components:
            component_name = component.pkg_names[self.installer_name]
            args = self.queries[self.query_name]["version"] + [component_name]
            result = self.query.__getitem__(args) & TEE
            if result[0] != 0:
                versions[component.name] = None
            else:
                versions[component.name] = str(result[1]).strip()
        return versions

class Pip(Generic):
    ''' Install components using the pip command line tool '''
    def __init__(self, components, component_config):
        Generic.__init__(self, components, component_config)

    def _install(self):
        pass

    def _versions(self):
        return {}
