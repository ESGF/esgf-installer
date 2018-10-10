''' Handle the installation, updating and general management of components '''
import json
import logging

from backports import configparser

from .install_codes import OK, NOT_INSTALLED, BAD_VERSION

class Installer(object):
    '''
    A class for handling the installation, updating and general management of components.
    Takes a dictionary of components and find their assignments and a list of components names
    that specify what components to install.
    '''
    def __init__(self, requirements, name_spec, is_control=False, is_install=False):
        self.log = logging.getLogger(__name__)
        self.methods = []
        self.controlled_components = []

        requirements = self._interpolate(requirements)
        # print json.dumps(requirements, indent=2, sort_keys=True)
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
        if is_install:
            ordered, unordered = self._resolve_order(requirements, names)
        else:
            ordered, unordered = ([], names)

        if unordered:
            self._init_unordered(requirements, unordered)
        if ordered:
            self._init_ordered(requirements, ordered)

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
            method.install(not_installed)

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

    def _init_ordered(self, requirements, ordered):
        prev_method_type = None
        common_method_type = []
        for name in ordered:
            config = requirements[name]
            config["name"] = name
            if "controller" in config:
                controller = config["controller"]
                self.controlled_components.append(controller(name, config))
            method_type = config["method"]
            if prev_method_type and prev_method_type == method_type:
                common_method_type.append(config)
            elif not common_method_type:
                common_method_type = [config]
            else:
                self.methods.append(prev_method_type(common_method_type))
                common_method_type = [config]
            prev_method_type = method_type
        self.methods.append(prev_method_type(common_method_type))

    def _init_unordered(self, requirements, unordered):
        assignments = {}
        for name in unordered:
            config = requirements[name]
            config["name"] = name
            method_type = config["method"]
            if method_type not in assignments:
                assignments[method_type] = []
            # Assign and initialize this component
            assignments[method_type].append(config)
            if "controller" in config:
                controller = config["controller"]
                self.controlled_components.append(controller(name, config))
        # Initialize methods with components
        for method in assignments:
            components = assignments[method]
            self.methods.append(method(components))

    def _resolve_order(self, requirements, names):
        all_requires = {}
        for name in requirements:
            config = requirements[name]
            try:
                all_requires[name] = config["requires"]
            except KeyError:
                pass
        dependencies = {}
        for name in names:
            config = requirements[name]
            try:
                dependencies[name] = config["requires"]
            except KeyError:
                pass
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

        all_requires[None] = root_names
        ordered = []
        seen = []
        self._dep_resolve(all_requires, None, ordered, seen)
        ordered = ordered[:-1]
        unordered = set(names) - (set(names) & set(ordered))

        # Return a list in a required order, and a list with no required ordered
        # Exclude the last element as it is the psuedo-component None used above
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

    def _interpolate(self, requirements):

        string_only = {}
        for name in requirements:
            config = requirements[name]
            string_only[name] = {"name": name}
            for param in config:
                if isinstance(param, basestring):
                    string_only[name][param] = config[param]

        parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        parser.read_dict(string_only)

        for name in parser:
            for param in parser[name]:
                requirements[name][param] = parser[name][param]

        return requirements
