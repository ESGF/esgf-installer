
from plumbum import local
from plumbum import TEE

from .generic import Generic

class Command(Generic):
    ''' Install components using and arbibtrary command '''
    def __init__(self, components):
        Generic.__init__(self, components)
        self.executed = set()

    def _install(self, names):
        for component in self.components:
            if component["name"] not in names:
                continue
            cmd = local.get(component["command"])
            try:
                args = component["args"]
            except KeyError:
                result = cmd.run_tee()
            else:
                result = cmd.__getitem__(args) & TEE
            self.executed.add(component["name"])

    def _uninstall(self):
        pass

    def _versions(self):
        versions = {}
        for component in self.components:
            if component["name"] in self.executed:
                versions[component["name"]] = "1"
            else:
                versions[component["name"]] = None
        return versions
