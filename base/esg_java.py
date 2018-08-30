import os
import logging
from distutils.spawn import find_executable
from esgf_utilities import pybash
from esgf_utilities import esg_functions
from esgf_utilities import esg_version_manager
from esgf_utilities.esg_exceptions import SubprocessError
from esgf_utilities.esg_env_manager import EnvWriter

from installer import install_codes
from esg_init import JavaConfig
from esg_init import AntConfig
logger = logging.getLogger("esgf_logger" + "." + __name__)

class Java(JavaConfig):
    def __init__(self):
        JavaConfig.__init__(self)
        logger.debug("Initialize a Java component")
        self.java_bin_path = os.path.join(self.java_install_dir, "bin", "java")
        self.existing_version = None

    def version(self):
        '''Checks the Java version on the system'''
        if pybash.is_exe(self.java_bin_path):
            logger.debug("java_bin_path: %s", self.java_bin_path)
            try:
                java_version_output = esg_functions.call_subprocess(
                    "{} -version".format(self.java_bin_path)
                )["stderr"]
            except SubprocessError:
                logger.error("Could not check the Java version")
                raise
            version_line = java_version_output.split("\n")[0]
            version = version_line.split(" ")[2]
            self.existing_version = version.strip("\"")

            return self.existing_version
        return None

    def status(self):
        '''Check status of this components installation, return respective code to the Installer'''
        self.existing_version = self.version()
        if self.existing_version is not None:
            valid_version = esg_version_manager.compare_versions(self.existing_version, self.java_version)
            if valid_version:
                return install_codes.OK
            else:
                return install_codes.BAD_VERSION
        return install_codes.NOT_INSTALLED

    def _download(self, java_tarfile):
        '''Download Java from distribution mirror'''
        logger.debug("Downloading Java from %s", self.java_dist_url)
        if not esg_functions.download_update(java_tarfile, self.java_dist_url):
            logger.error("ERROR: Could not download Java")
            raise RuntimeError
    def install(self):
        '''Called by the Installer if this component needs to be installed'''
        esg_functions.install_header("Java", version=self.java_version)
        pybash.mkdir_p(self.workdir)
        with pybash.pushd(self.workdir):

            java_tarfile = pybash.trim_string_from_head(self.java_dist_url)
            jdk_directory = java_tarfile.split("-")[0]
            java_install_dir_parent = self.java_install_dir.rsplit("/", 1)[0]

            # Check for Java tar file
            if not os.path.isfile(java_tarfile):
                logger.debug(
                    "Don't see java distribution file %s",
                    os.path.join(os.getcwd(), java_tarfile)
                )
                self._download(java_tarfile)

            logger.debug("Extracting Java tarfile %s", java_tarfile)
            esg_functions.extract_tarball(java_tarfile, java_install_dir_parent)

            # Create symlink to Java install directory (/usr/local/java)
            pybash.symlink_force(
                os.path.join(
                    java_install_dir_parent,
                    jdk_directory
                ),
                self.java_install_dir
            )

            # NOTE Since root downloaded and installed, are they not the owner?
            # Is it desired to have someone other than root the owner?
            os.chown(self.java_install_dir, self.installer_uid, self.installer_gid)
            # recursively change permissions
            esg_functions.change_ownership_recursive(
                self.java_install_dir, self.installer_uid, self.installer_gid)

            self.post_install()

    def post_install(self):
        '''Writes Java config to install manifest and env'''
        logger.debug("java %s %s", self.java_install_dir, self.version())
        esg_functions.write_to_install_manifest(
            "java",
            self.java_install_dir,
            self.version()
        )
        EnvWriter.write("JAVA_HOME", self.java_install_dir,)

class Ant(AntConfig):
    def __init__(self):
        AntConfig.__init__(self)
        self.existing_version = None
        logger.debug("Initialize an Ant component")

    def version(self):
        ''' Gets the version of ant using "ant -version" '''
        if find_executable("ant") is not None:
            version_output = esg_functions.call_subprocess("ant -version")['stdout']
            self.existing_version = version_output.split(" ")[3]
            logger.debug("ant %s %s", find_executable("ant"), self.existing_version)
            return self.existing_version
        return None

    def status(self):
        '''Check status of this components installation, return respective code to the Installer'''
        self.existing_version = self.version()
        if self.existing_version is not None:
            # valid_version = esg_version_manager.compare_versions(self.existing_version, self.ant_version)
            return install_codes.OK
        return install_codes.NOT_INSTALLED

    def install(self):
        '''Called by the Installer if this component needs to be installed'''
        esg_functions.install_header("Ant")

        esg_functions.stream_subprocess_output("yum -y install ant")

        self.post_install()

    def post_install(self):
        '''Writes Ant config to install manifest and env'''
        EnvWriter.write("ANT_HOME", find_executable("ant"))
        logger.debug("ant %s %s", find_executable("ant"), self.version())
        esg_functions.write_to_install_manifest("ant", find_executable("ant"), self.version())
