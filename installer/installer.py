
from base.esg_java import Java, Ant
from .methods import PackageManager, Mirror
from .install_codes import OK, NOT_INSTALLED, BAD_VERSION

class Installer(object):
    # A class for handling the installation, updating and general management of components
    def __init__(self, node):
        # Store what components are needed for each node type.
        node_types = {
            # "data": { Foo },
            # "index": { Foo, Bar }
            "base": { Java, Ant }
        }
        # Find unique components, as there may be overlap
        component_types = set()
        for node_type in node:
            component_types |= node_types[node_type]

        method_types = {
            PackageManager: { Ant },
            Mirror: { Java }
        }
        methods = set()
        for method_type in method_types:
            components = method_types[method_type] & component_types
            methods.add(method_type(components))

        for method in methods:
            method.install()


        self.components_status = {
            OK: [],
            NOT_INSTALLED: [],
            BAD_VERSION: []
        }
        self.divider = "_"*30
        self.header = self.divider + "\n{}"

        #
        #
        #
        # # Initialize the unique types
        # self.components = []
        # print self.header.format("Creating objects")
        # for component in component_types:
        #     print "    {}".format(component.__name__)
        #     self.components.append(component())

    def status_check(self):
        # Check the status of of component
        print self.header.format("Checking status")
        for component in self.components:
            print "    {}".format(type(component).__name__)
            self.components_status[component.status()].append(component)

        if len(self.components_status[NOT_INSTALLED]) != 0:
            print self.header.format("Not installed:")
            for component in self.components_status[NOT_INSTALLED]:
                print "    {}".format(type(component).__name__)
        if len(self.components_status[BAD_VERSION]) != 0:
            print self.header.format("Invalid Version:")
            for component in self.components_status[BAD_VERSION]:
                print "    {}".format(type(component).__name__)
        if len(self.components_status[OK]) != 0:
            print self.header.format("Already Installed:")
            for component in self.components_status[OK]:
                print "    {} {}".format(type(component).__name__, component.version())

    def install(self):
        for component in self.components_status[NOT_INSTALLED]:
            self.learn_properties(component)
        # Handle components based on their status
        pass
