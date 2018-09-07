from .installer import Installer

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
            "types": "base"
        }
    def start(self):
        print "Starting Director"
        if self.params["install"]:
            installer = Installer(self.params["types"].split())
            # installer.status_check()
            # installer.install()
