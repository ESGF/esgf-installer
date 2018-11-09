import logging

from ..constants import OK, NOT_INSTALLED, BAD_VERSION

class Generic(object):
    def __init__(self, components):
        self.log = logging.getLogger(__name__)
        self.components = components

    def uninstall(self):
        self._uninstall()

    def _uninstall(self):
        ''' Generic version, should be reimplemented by children '''
        pass

    def install(self, names):
        ''' Entry function to perform an installation '''
        self._install(names)

    def _install(self, names):
        ''' Generic version, should be reimplemented by children '''
        pass

    def statuses(self):
        ''' Entry function to get the statuses '''
        return self._statuses()

    def _statuses(self):
        ''' As long as versions is implemented correctly this is all that a status check is '''
        versions = self.versions()
        statuses = {}
        for component in self.components:
            name = component["name"]
            version = versions[name]
            
            if version is None:
                statuses[name] = NOT_INSTALLED
            else:
                req_version = None
                try:
                    req_version = component["tag"]
                except KeyError:
                    pass
                try:
                    req_version = component["version"]
                except KeyError:
                    pass
                if req_version is None:
                    statuses[name] = OK
                elif req_version != version:
                    statuses[name] = BAD_VERSION
                else:
                    statuses[name] = OK
        return statuses

    def versions(self):
        ''' Entry function to get versions '''
        return self._versions()

    def _versions(self):
        ''' Generic version, should be reimplemented by children '''
        versions = {}
        for component in self.components:
            versions[component["name"]] = None
        return versions
