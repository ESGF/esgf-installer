import os
import zipfile
import tarfile

import requests

from ..utils import mkdir_p, chown_R
from .generic import Generic

class DistributionArchive(Generic):
    ''' Install components from a URL '''
    def __init__(self, components, component_config):
        Generic.__init__(self, components, component_config)
        self.tmp = os.path.join(os.sep, "tmp")
        self.chunk_size = 1*1024

    def _install(self):
        for component in self.components:
            remote_file = component.url.rsplit('/', 1)[-1]
            try:
                local_dir = component.local_dir
            except AttributeError:
                local_dir = self.tmp
            mkdir_p(local_dir)
            filename = os.path.join(local_dir, remote_file)
            #if not os.path.isfile(filename):
            response = requests.get(component.url, stream=True)
            with open(filename, 'wb') as localfile:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    localfile.write(chunk)

            try:
                extract_dir = component.extract_dir
            except AttributeError:
                pass #TODO fill in these except blocks with logging messages
            else:
                mkdir_p(extract_dir)
                if tarfile.is_tarfile(filename):
                    with tarfile.TarFile(filename, "r") as archive:
                        archive.extractall(extract_dir)
                elif zipfile.is_zipfile(filename):
                    with zipfile.ZipFile(filename, "r") as archive:
                        archive.extractall(extract_dir)
                else:
                    print "Not a compressed file"
                filename = extract_dir
            try:
                chown_R(filename, component.owner_uid, component.owner_gid)
            except AttributeError:
                pass
