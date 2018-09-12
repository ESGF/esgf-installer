import os
import zipfile

import requests

from .generic import Generic

class DistributionArchive(Generic):
    ''' Install components from a URL '''
    def __init__(self, components, component_config):
        Generic.__init__(self, components, component_config)
        self.tmp = os.path.join(os.sep, "tmp")
        self.chunk_size = 1*1024

    def _install(self):
        for component in self.components:
            remote_file = component.url.rsplit('/', 1)
            try:
                local_dir = component.local_dir
            except AttributeError:
                local_dir = self.tmp
            filename = os.path.join(local_dir, remote_file)
            #if not os.path.isfile(filename):
            response = requests.get(component.url, stream=True)
            with open(filename, 'wb') as localfile:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    localfile.write(chunk)
            try:
                extract_dir = component.extract_dir
            except AttributeError:
                pass
            else:
                #mkdir --p extract_dir
                with zipfile.Zipfile(filename) as archive:
                    archive.extractall(extract_dir)
