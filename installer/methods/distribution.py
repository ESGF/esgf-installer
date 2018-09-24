import logging
import os
import shutil
import tarfile
import zipfile

import requests

from ..utils import mkdir_p, chown_R
from .generic import Generic

class FileManager(Generic):
    ''' Install components from a url '''
    def __init__(self, components):
        Generic.__init__(self, components)
        self.log = logging.getLogger(__name__)
        self.tmp = os.path.join(os.sep, "tmp")
        self.chunk_size = 1*1024

    def _install(self, names):
        for component in self.components:
            if component.name not in names:
                continue

            if not os.path.isfile(component.source):
                source = self._get_remote(component)
            else:
                source = component.source

            filepath = self._extract(source, component)

            try:
                chown_R(filepath, component.owner_uid, component.owner_gid)
            except AttributeError:
                pass

    def _get_remote(self, component):
        url = component.source
        remote_file = url.rsplit('/', 1)[-1]
        # # mkdir_p(download_dir)
        filename = os.path.join(self.tmp, remote_file)
        #if not os.path.isfile(filename):
        response = requests.get(url, stream=True)
        with open(filename, 'wb') as localfile:
            for chunk in response.iter_content(chunk_size=self.chunk_size):
                localfile.write(chunk)
        return filename

    def _extract(self, filepath, component):
        if tarfile.is_tarfile(filepath) and component.extract:
            try:
                tar_root_dir = component.tar_root_dir
            except AttributeError:
                with tarfile.open(filepath) as archive:
                    archive.extractall(component.dest)
            else:
                with tarfile.open(filepath) as archive:
                    archive.extractall(self.tmp)
                tmp_filepath = os.path.join(self.tmp, tar_root_dir)
                shutil.move(tmp_filepath, component.dest)
            return component.dest
        elif zipfile.is_zipfile(filepath) and component.extract:
            with zipfile.ZipFile(filepath, "r") as archive:
                archive.extractall(component.dest)
            return component.dest
        else:
            # Not a tar or zip file or do not extract
            name = os.path.basename(filepath)
            dest_filepath = os.path.join(component.dest, name)
            mkdir_p(dest_filepath)
            shutil.move(filepath, dest_filepath)
            return dest_filepath

    def _versions(self):
        #TODO This only checks for existence of files, maybe do a little more, md5 checksum?
        versions = {}
        for component in self.components:
            if os.path.isfile(component.dest):
                versions[component.name] = "1"
            elif os.path.isdir(component.dest) and os.listdir(component.dest):
                versions[component.name] = "1"
            else:
                versions[component.name] = None
        return versions
