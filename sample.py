
# Codes to be used by Installer to figure out what to do
OK = 0
NOT_INSTALLED = 1
BAD_VERSION = 2

# A sample utility function
def version_check(v1, v2):
    if int(v1) != int(v2):
        return BAD_VERSION
    return OK

# A common config option to be inherited by many components
class BaseConfig(object):
    def __init__(self):
        self.shared_value = "base_directory"

# A sample component config
class FooConfig(BaseConfig):
    def __init__(self):
        BaseConfig.__init__(self)
        self.foo_location = "foo.txt"
        self.foo_version = "1"

# A sample component config
class BarConfig(BaseConfig):
    def __init__(self):
        BaseConfig.__init__(self)
        self.bar_location = "bar.txt"
        self.bar_version = "2"

# A sample component config
class BazConfig(BarConfig, FooConfig):
    def __init__(self):
        BarConfig.__init__(self)
        FooConfig.__init__(self)
        self.baz_value = 3

# A sample component
class Foo(FooConfig):
    def __init__(self):
        # Initialize config
        FooConfig.__init__(self)

    def status(self):
        # A simple status checker
        print "Checking component Foo's status"
        try:
            foo_file = open(self.foo_location, 'r')
        except IOError:
            print "Foo not installed", self.foo_location
            return NOT_INSTALLED
        existing_version = int(foo_file.read().strip())
        print "Foo {} installed (Want {})".format(existing_version, self.foo_version)
        return version_check(existing_version, self.foo_version)

    def install(self):
        print "****\nInstalling Foo\n****"
        with open(self.foo_location, "w") as foo_file:
            foo_file.write(self.foo_version)
        # Anything that needs to happen after the install, like a check or test
        self.post_install()

    def post_install(self):
        print "Post install in Foo"
        self.status()

class Bar(BarConfig):
    def __init__(self):
        BarConfig.__init__(self)

    def status(self):
        print "Checking component Bar's status"
        try:
            bar_file = open(self.bar_location, 'r')
        except IOError:
            print "Bar not installed", self.bar_location
            return NOT_INSTALLED
        existing_version = int(bar_file.read().strip())
        print "Bar {} installed (Want {})".format(existing_version, self.bar_version)
        return version_check(existing_version, self.bar_version)

    def install(self):
        print "****\nInstalling Bar\n****"
        with open(self.bar_location, "w") as bar_file:
            bar_file.write(self.bar_version)

        self.post_install()

    def post_install(self):
        # write to env file
        # write to log
        print "Post install in Bar"
        self.status()

class Installer(object):
    # A class for handling the installation, updating and general management of components
    def __init__(self, node_types):
        # Store what components are needed for each node type.
        nodes = {
            "data": [ Bar ],
            "index": [ Foo, Bar ]
        }
        # Find unique components, as there may be overlap
        component_types = set()
        for node in node_types:
            for component in nodes[node]:
                component_types.add(component)

        # Initialize the unique types and give them a dictionary to store information
        self.components = {}
        for component in component_types:
            self.components[component()] = {"status": None}
        print "Initialized Components:", self.components

    def status_check(self):
        # Check the status of of component
        for component in self.components:
            self.components[component]["status"] = component.status()

    def install(self):
        # Handle components based on their status
        for component in self.components:
            if self.components[component]["status"] != OK:
                component.install()

class Director(object):
    # A class for managing the flow of the program
    def __init__(self):
        self.params = None

    def pre_check(self):
        # Check privileges, OS, etc..
        print "Checking prerequisites..."

    def get_cmd_line(self):
        # A sample input from cmd line
        self.params = {
            "install" : True,
            "types": "data index"
        }
    def start(self):
        print "Starting Director"
        if self.params["install"]:
            installer = Installer(self.params["types"].split())
            installer.status_check()
            installer.install()


if __name__ == "__main__":
    director = Director()
    director.pre_check()
    director.get_cmd_line()
    director.start()
