''' Handle the installation, updating and general management of components '''
import json
import logging

from .install_codes import OK, NOT_INSTALLED, BAD_VERSION

class Installer(object):
    '''
    A class for handling the installation, updating and general management of components.
    Takes a dictionary of components and find their assignments and a list of components names
    that specify what components to install.
    '''
    def __init__(self, requirements, name_spec, is_control=False):
        self.log = logging.getLogger(__name__)
        self.methods = []
        self.controlled_components = []
        self.assignments = {}
        names = []
        for name in requirements:
            if name_spec and name not in name_spec:
                continue
            # The configuartion details for this component
            config = requirements[name]
            # If doing a control cmd (start, stop, restart) only init controlled components
            if is_control and "controller" not in config:
                continue
            names.append(name)

        ordered, unordered = self._resolve_order(requirements, names)
        for name in names:
            config = requirements[name]
            method_type = config["method"]
            component_type = config["type"]
            if method_type not in self.assignments:
                self.assignments[method_type] = []
            # Assign and initialize this component
            self.assignments[method_type].append(component_type(name, config))

            if "controller" in config:
                controller = config["controller"]
                self.controlled_components.append(controller(name, config))

        # Initialize methods with components
        for method in self.assignments:
            components = self.assignments[method]
            self.methods.append(method(components))

        self.divider = "_"*30
        self.header = self.divider + "\n{}"


    def status_check(self):
        ''' Check the installation status of each component '''
        print self.header.format("Checking status")
        statuses = {}
        for method in self.methods:
            statuses.update(method.statuses())
        print json.dumps(statuses, indent=2, sort_keys=True)
        return statuses

    def uninstall(self):
        ''' Uninstall each component '''
        print self.header.format("Uninstalling")
        self.status_check()
        for method in self.methods:
            method.uninstall()
        self.status_check()

    def install(self):
        '''
        Install each component, allow for each component to take action before and
        after the primary install step via pre_install and post_install methods
        '''
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

    def versions(self):
        ''' Print the currently installed verison of each component '''
        print self.header.format("Checking versions")
        versions = {}
        for method in self.methods:
            versions.update(method.versions())
        print json.dumps(versions, indent=2, sort_keys=True)

    def start(self):
        ''' Start each controlled component '''
        print self.header.format("Starting")
        statuses = self.status_check()
        not_installed = [name for name in statuses if statuses[name] == NOT_INSTALLED]
        for component in self.controlled_components:
            if component.name in not_installed:
                print "{} not installed, cannot start.".format(component.name)
                continue
            component.start()

    def stop(self):
        ''' Stop each controlled component '''
        print self.header.format("Stopping")
        statuses = self.status_check()
        not_installed = [name for name in statuses if statuses[name] == NOT_INSTALLED]
        for component in self.controlled_components:
            if component.name in not_installed:
                print "{} not installed, cannot stop.".format(component.name)
                continue
            component.stop()

    def restart(self):
        ''' Restart each controlled component '''
        print self.header.format("Restarting")
        statuses = self.status_check()
        not_installed = [name for name in statuses if statuses[name] == NOT_INSTALLED]
        for component in self.controlled_components:
            if component.name in not_installed:
                print "{} not installed, cannot restart.".format(component.name)
                continue
            component.restart()

    def _resolve_order(self, requirements, names):
        unordered = []
        dependencies = {}
        for name in names:
            config = requirements[name]
            try:
                dependencies[name] = config["requires"]
            except KeyError:
                unordered.append(name)
        # Get components that no other components depend on
        root_names = []
        for name_a in dependencies:
            is_root = True
            for name_b in dependencies:
                if name_a in dependencies[name_b]:
                    is_root = False
                    break
            if is_root:
                root_names.append(name_a)

        dependencies[None] = root_names
        ordered = []
        seen = []
        self._dep_resolve(dependencies, None, ordered, seen)
        print ordered
        # TODO use the resolved information above to determine order
        return (ordered, unordered)

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
