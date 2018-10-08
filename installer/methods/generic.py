import logging

from ..install_codes import OK, NOT_INSTALLED, BAD_VERSION
from ..utils import populate
from ..utils import populated
from ..utils import check_populatable

class Generic(object):
    def __init__(self, components):
        self.log = logging.getLogger(__name__)
        self.components = []
        for component in components:
            component = self._format_component(component)
            self.components.append(component)

    def _format_component(self, config):
        name = config["name"]
        replacements = {"name": name}
        for param in config:
            if not isinstance(config[param], basestring):
                continue
            check_populatable(param, config[param], config.keys()+replacements.keys())
        all_populated = False
        while not all_populated:
            all_populated = True
            for param in config:
                if not isinstance(config[param], basestring):
                    continue
                if param in replacements:
                    continue
                if populated(config[param]):
                    replacements[param] = config[param]
                else:
                    config[param] = populate(config[param], replacements)
                    all_populated = False
        return config

    def uninstall(self):
        self._uninstall()

    def _uninstall(self):
        for component in self.components:
            try:
                component.uninstall()
            except AttributeError:
                self.log.warning("Do not know how to uninstall %s", component.name)

    def pre_install(self):
        ''' Entry function to perform pre installation '''
        self._pre_install()

    def install(self, names):
        ''' Entry function to perform an installation '''
        self._install(names)

    def post_install(self):
        ''' Entry function to perform post installation '''
        self._post_install()

    def _pre_install(self):
        ''' Allows for components to take actions before installation '''
        for component in self.components:
            try:
                component.pre_install()
            except AttributeError:
                continue

    def _install(self, names):
        ''' Generic version, should be reimplemented by children '''
        for component in self.components:
            if component.name not in names:
                continue
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
