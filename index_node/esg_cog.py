import os
import shutil
import logging
import ConfigParser
import yaml
from git import Repo, GitCommandError
from esgf_utilities import esg_functions
from esgf_utilities import pybash
from esgf_utilities import esg_property_manager
from esgf_utilities.esg_exceptions import SubprocessError


logger = logging.getLogger("esgf_logger" +"."+ __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

#TODO: This is duplicating checkout_publisher_branch in esg_publisher; Should be generalized
def checkout_cog_branch(cog_path, branch_name):
    '''Checkout a given branch of the COG repo'''
    publisher_repo_local = Repo(cog_path)
    publisher_repo_local.git.checkout(branch_name)
    return publisher_repo_local

def clone_cog_repo(COG_INSTALL_DIR, COG_TAG="master"):
    '''Clone the COG repo from Github'''
    print "\n*******************************"
    print "Cloning COG repo"
    print "******************************* \n"

    from git import RemoteProgress
    class Progress(RemoteProgress):
        def update(self, op_code, cur_count, max_count=None, message=''):
            if message:
                print('Downloading: (==== {} ====)\r'.format(message))
                print "current line:", self._cur_line

    # Repo.clone_from("https://github.com/EarthSystemCoG/COG.git", COG_INSTALL_DIR, progress=Progress())
    Repo.clone_from("https://github.com/William-Hill/COG.git", COG_INSTALL_DIR, progress=Progress())
    # checkout_cog_branch(COG_INSTALL_DIR, COG_TAG)
    checkout_cog_branch(COG_INSTALL_DIR, "ESGF_3.0")

def transfer_api_client_python(target_directory):
    print "\n*******************************"
    print "Setting up Transfer API Client"
    print "******************************* \n"
    if os.path.isdir(target_directory):
        logger.info("target_directory %s already exists. Skipping cloning from Github", target_directory)
    else:
        Repo.clone_from("https://github.com/globusonline/transfer-api-client-python.git", target_directory)
    with pybash.pushd(target_directory):
        repo = Repo(os.path.join(target_directory))
        git = repo.git
        git.pull()
        with pybash.pushd("mkproxy"):
            esg_functions.stream_subprocess_output("make install")

def change_cog_dir_owner(COG_DIR, COG_CONFIG_DIR):
    # change ownership of COG_CONFIG_DIR/site_media
    apache_user = esg_functions.get_user_id("apache")
    apache_group = esg_functions.get_group_id("apache")
    esg_functions.change_ownership_recursive("{COG_DIR}".format(COG_DIR=COG_DIR), apache_user, apache_group)
    esg_functions.change_ownership_recursive("{COG_CONFIG_DIR}".format(COG_CONFIG_DIR=COG_CONFIG_DIR), apache_user, apache_group)

    # # create location where Python eggs can be unpacked by user 'apache'
    PYTHON_EGG_CACHE_DIR = "/var/www/.python-eggs"
    esg_functions.change_ownership_recursive("{PYTHON_EGG_CACHE_DIR}".format(PYTHON_EGG_CACHE_DIR=PYTHON_EGG_CACHE_DIR), apache_user, apache_group)

def setup_cog(COG_DIR="/usr/local/cog"):
    if os.path.isdir("/usr/local/cog"):
        print "Cog directory found."
        try:
            setup_cog_answer = esg_property_manager.get_property("update.cog")
        except ConfigParser.NoOptionError:
            setup_cog_answer = raw_input(
                "Do you want to contine the CoG installation [y/N]: ") or "no"
        if setup_cog_answer.lower() in ["no", "n"]:
            print "Using existing CoG setup. Skipping installation"
            return False

    # choose CoG version
    COG_TAG = "v3.10.1"
    # setup CoG environment
    pybash.mkdir_p(COG_DIR)

    COG_CONFIG_DIR = "{COG_DIR}/cog_config".format(COG_DIR=COG_DIR)
    pybash.mkdir_p(COG_CONFIG_DIR)

    COG_INSTALL_DIR= "{COG_DIR}/cog_install".format(COG_DIR=COG_DIR)
    pybash.mkdir_p(COG_INSTALL_DIR)

    os.environ["LD_LIBRARY_PATH"] = "/usr/local/lib"
    try:
        clone_cog_repo(COG_INSTALL_DIR, COG_TAG)
    except GitCommandError, error:
        logger.exception("Failed to clone COG repo: \n %s", error)

    # XXX The git url for django openid auth is a fork at v0.7
    #  of the real project. The real project is now at v0.14,
    #  but has very little development currently
    esg_functions.pip_install_git(
        "https://github.com/EarthSystemCoG/django-openid-auth.git",
        "django-openid-auth"
    )
    # install CoG dependencies
    with pybash.pushd(COG_INSTALL_DIR):
        # "pip install -r requirements.txt"
        esg_functions.pip_install("requirements.txt", req_file=True)

        # Build and install mkproxy
        transfer_api_client_python(os.path.join(COG_DIR, "transfer-api-client-python"))

        # setup CoG database and configuration
        esg_functions.stream_subprocess_output("python setup.py install")

        # create or upgrade CoG installation
        esg_functions.stream_subprocess_output("python setup.py setup_cog --esgf=true")

        # collect static files to ./static directory
        esg_functions.stream_subprocess_output("python manage.py collectstatic --no-input")

    # create non-privileged user to run django
    try:
        esg_functions.stream_subprocess_output("groupadd -r cogadmin")
    except SubprocessError, error:
        logger.debug(error.__dict__["data"]["returncode"])
        if error.__dict__["data"]["returncode"] == 9:
            pass
    try:
        esg_functions.stream_subprocess_output("useradd -r -g cogadmin cogadmin")
    except SubprocessError, error:
        logger.debug(error.__dict__["data"]["returncode"])
        if error.__dict__["data"]["returncode"] == 9:
            pass

    pybash.mkdir_p("~cogadmin")
    esg_functions.stream_subprocess_output("chown cogadmin:cogadmin ~cogadmin")

    # change user prompt
    with open("~cogadmin/.bashrc", "a") as cogadmin_bashrc:
        cogadmin_bashrc.write('export PS1="[\u@\h]\$ "')

    change_cog_dir_owner(COG_DIR, COG_CONFIG_DIR)

def main():
    setup_cog()

if __name__ == '__main__':
    main()
