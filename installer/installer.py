import json
import logging

from .install_codes import OK, NOT_INSTALLED, BAD_VERSION

class Installer(object):
    # A class for handling the installation, updating and general management of components
    def __init__(self, requirements, name_spec):
        self.log = logging.getLogger(__name__)
        self.methods = []
        dependencies = {}
        for method_type in requirements:
            component_reqs = requirements[method_type]
            components = []
            for name in component_reqs:
                if not name_spec or name in name_spec:
                    config = component_reqs[name]
                    if "requires" in config:
                        dependencies[name] = config["requires"]
                    component_type = config["type"]
                    components.append(component_type(name, config))
            if components:
                method = method_type(components)
                self.methods.append(method)

        for name in dependencies:
            resolved = []
            seen = []
            print name
            self._dep_resolve(dependencies, name, resolved, seen)
            print "resolved "+str(resolved)

        self.divider = "_"*30
        self.header = self.divider + "\n{}"

    def _dep_resolve(self, components, name, resolved, seen):
        seen.append(name)
        try:
            requires = components[name]
        except KeyError:
            resolved.append(name)
            return
        for dep in requires:
            if dep not in resolved:
                if dep in seen:
                    raise Exception('Circular reference detected: %s->%s' % (name, dep))
                self._dep_resolve(components, dep, resolved, seen)
        resolved.append(name)


    def status_check(self):
        # Check the status of each component
        print self.header.format("Checking status")
        statuses = {}
        for method in self.methods:
            statuses.update(method.statuses())
        print json.dumps(statuses, indent=2, sort_keys=True)
        return statuses

    def uninstall(self):
        print self.header.format("Uninstalling")
        self.status_check()
        for method in self.methods:
            method.uninstall()
        self.status_check()

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
