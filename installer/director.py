import logging

from .installer import Installer
from .components import ALL, CONTROL

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
            # self.args.status
        )
        if init_installer:
            # Find required methods and components
            requirements = {}
            include = set(["base"])
            exclude = set(["test"])

            if self.args.type:
                if set(self.args.type) != exclude:
                    node_types = set(self.args.type) | include
                else:
                    node_types = set(self.args.type)
            else:
                node_types = set(ALL.keys()) - exclude

            for node_type in node_types:
                requirements.update(ALL[node_type])

            component_spec = []
            if self.args.start is not None:
                for node_type in node_types:
                    component_spec += CONTROL[node_type]["start"]
            elif self.args.stop is not None:
                for node_type in node_types:
                    component_spec += CONTROL[node_type]["stop"]
            elif self.args.restart is not None:
                for node_type in node_types:
                    component_spec += CONTROL[node_type]["restart"]
            # elif self.args.status is not None:
            #     for node_type in node_types:
            #         component_spec += CONTROL[node_type]["status"]
            else:
                component_spec = (
                    self.args.install or
                    self.args.uninstall or
                    None
                )

            if component_spec is not None:
                component_spec = set(component_spec)

            installer = Installer(
                requirements,
                component_spec,
                self.args.input_params,
                is_install=self.args.install is not None or is_control_cmd
            )
            if self.args.install is not None or is_control_cmd:
                installer.install()
            elif self.args.uninstall is not None:
                installer.uninstall()
            elif self.args.freeze:
                installer.versions()
