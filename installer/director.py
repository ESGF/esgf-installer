import logging

from .installer import Installer
from .components import ALL

class Director(object):
    ''' A class for managing the flow of the program '''
    def __init__(self, args):
        self.log = logging.getLogger(__name__)
        self.args = args

    def pre_check(self):
        # Check privileges, OS, PATH, etc..
        print "Checking prerequisites"

    def begin(self):
        print "Starting Director"
        init_installer = (
            self.args.install is not None or
            self.args.uninstall is not None or
            self.args.start is not None or
            self.args.stop is not None or
            self.args.restart is not None or
            self.args.freeze
        )
        is_control_cmd = (
            self.args.start is not None or
            self.args.stop is not None or
            self.args.restart is not None
        )
        if init_installer:
            # Find required methods and components
            requirements = {}
            if self.args.type:
                node_types = self.args.type
            else:
                node_types = ALL.keys()
            for node_type in node_types:
                requirements.update(ALL[node_type])

            component_spec = (
                self.args.install or
                self.args.uninstall or
                self.args.start or
                self.args.stop or
                self.args.restart or
                None
            )
            installer = Installer(
                requirements,
                component_spec,
                is_control=is_control_cmd,
                is_install=self.args.install is not None
            )
            if self.args.install is not None:
                installer.install()
                # installer.start()
            elif self.args.uninstall is not None:
                installer.uninstall()
            elif self.args.start is not None:
                installer.start()
            elif self.args.stop is not None:
                installer.stop()
            elif self.args.restart is not None:
                installer.restart()
            elif self.args.freeze:
                installer.versions()
