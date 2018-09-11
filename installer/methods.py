''' Common methods for performing installations within the ESGF stack '''
import os
from plumbum import local
from plumbum import TEE
from .install_codes import OK, NOT_INSTALLED, BAD_VERSION

class Generic(object):
    def __init__(self, components):
        self.components = [component() for component in components]

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
            name = type(component).__name__
            if versions[name] is None:
                statuses[name] = NOT_INSTALLED
            else:
                try:
                    # TODO: Make this a less naive version comparison
                    statuses[name] = OK if component.req_version == versions[name] else BAD_VERSION
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
            versions[type(component).__name__] = component.version()

class DistributionArchive(Generic):
    ''' Install components from a URL via some fetching tool (wget, fetch, etc.) '''
    def __init__(self, components):
        Generic.__init__(self, components)

    def _install(self):
        pass

class PackageManager(Generic):
    ''' System package managers, does not include pip (could it though?) '''
    def __init__(self, components):
        Generic.__init__(self, components)
        # Installer interface for different OS's
        self.installers = {
            "yum": {
                "install_y": ["install", "-y"]
            },
            "apt": {
                "install_y": ["install", "-y"]
            }
        }
        # Ways of querying for version/existence
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
        pkg_list = [component.pkg_names[self.installer_name] for component in self.components]
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
                versions[type(component).__name__] = None
            else:
                versions[type(component).__name__] = str(result[1]).strip()
        return versions

class Pip(Generic):
    ''' Install components using the pip command line tool '''
    def __init__(self, components):
        Generic.__init__(self, components)

    def _install(self):
        pass

    def _versions(self):
        return {}
