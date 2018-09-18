import os
import shutil
import tarfile
import zipfile

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
            print "Installing {}".format(component.name)
            remote_file = component.url.rsplit('/', 1)[-1]
            print "Remote file {}".format(remote_file)
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
                print "Extract dir {}".format(extract_dir)
                # TODO dangerous when root, put safe gaurds on rmtree
                if os.path.isdir(extract_dir):
                    shutil.rmtree(extract_dir)
                if tarfile.is_tarfile(filename):
                    with tarfile.open(filename) as archive:
                        try:
                            # The tarball is typically a single directory
                            tar_root_dir = component.tar_root_dir
                        except AttributeError:
                            # If there is not a single root directory that has been specified
                            mkdir_p(extract_dir)
                            archive.extractall(extract_dir)
                        else:
                            # If that is the case "extract" that root directory
                            # This is the alternative strategy to the symlinks previously being made
                            tar_dir = os.path.join(self.tmp, tar_root_dir)
                            if os.path.isdir(tar_dir):
                                shutil.rmtree(tar_dir)
                            archive.extractall(self.tmp)
                            shutil.move(tar_dir, extract_dir)

                elif zipfile.is_zipfile(filename):
                    mkdir_p(extract_dir)
                    with zipfile.ZipFile(filename, "r") as archive:
                        archive.extractall(extract_dir)
                else:
                    print "Not a tar or zip file"
                filename = extract_dir
            try:
                chown_R(filename, component.owner_uid, component.owner_gid)
            except AttributeError:
                pass
