import os

from plumbum import local
from plumbum import TEE

from ..files import FileComponent

class Java(FileComponent):
    def __init__(self, name, config):
        FileComponent.__init__(self, name, config)

    def version(self):
        java_path = os.path.join(self.extract_dir, "bin", "java")
        if os.path.isfile(java_path):
            java = local[java_path]
            result = java["-version"] & TEE
            java_version_output = result[2]
            version_line = java_version_output.split("\n")[0]
            return version_line.split("version")[1].strip()
        else:
            return None
