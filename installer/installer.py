import json

from .install_codes import OK, NOT_INSTALLED, BAD_VERSION

class Installer(object):
    # A class for handling the installation, updating and general management of components
    def __init__(self, requirements, name_spec):
        self.methods = []
        for method_type in requirements:
            component_reqs = requirements[method_type]
            components = []
            for name in component_reqs:
                if not name_spec or name in name_spec:
                    config = component_reqs[name]
                    component_type = config["type"]
                    components.append(component_type(name, config))
            if components:
                method = method_type(components)
                self.methods.append(method)
        self.divider = "_"*30
        self.header = self.divider + "\n{}"

    def status_check(self):
        # Check the status of each component
        print self.header.format("Checking status")
        statuses = {}
        for method in self.methods:
            statuses.update(method.statuses())
        print json.dumps(statuses, indent=2, sort_keys=True)
        return statuses

    def install(self):
        print self.header.format("Installing")
        statuses = self.status_check()
        not_installed = [name for name in statuses if statuses[name] == NOT_INSTALLED]
        for method in self.methods:
            method.pre_install()
        for method in self.methods:
            method.install(not_installed)
        for method in self.methods:
            method.post_install()
        statuses = self.status_check()

    def versions_installed(self):
        print self.header.format("Checking versions")
        versions = {}
        for method in self.methods:
            versions.update(method.versions())
        return versions
