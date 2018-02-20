import os
import shutil
import logging
import yaml
import pip
from git import Repo, GitCommandError
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py


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
    checkout_cog_branch(COG_INSTALL_DIR, COG_TAG)

#TODO:Probably need to add a force_install param to force an update
def setup_django_openid_auth(target_directory):
    print "\n*******************************"
    print "Setting up Django OpenID Auth"
    print "******************************* \n"

    if os.path.isdir(target_directory):
        logger.info("target_directory %s already exists. Skipping cloning from Github", target_directory)
    else:
        Repo.clone_from("https://github.com/EarthSystemCoG/django-openid-auth.git", target_directory)

    with esg_bash2py.pushd(target_directory):
        esg_functions.stream_subprocess_output("python setup.py install")

def transfer_api_client_python(target_directory):
    print "\n*******************************"
    print "Setting up Transfer API Client"
    print "******************************* \n"
    if os.path.isdir(target_directory):
        logger.info("target_directory %s already exists. Skipping cloning from Github", target_directory)
    else:
        Repo.clone_from("https://github.com/globusonline/transfer-api-client-python.git", target_directory)

    with esg_bash2py.pushd(target_directory):
        # esg_functions.stream_subprocess_output("python setup.py install")
        repo = Repo(os.path.join(target_directory))
        git = repo.git
        git.pull()
        with esg_bash2py.pushd("mkproxy"):
            esg_functions.stream_subprocess_output("make")
            shutil.copyfile("mkproxy", "/usr/local/conda/envs/esgf-pub/lib/python2.7/site-packages/globusonline/transfer/api_client/x509_proxy/mkproxy")

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
    # choose CoG version
    COG_TAG = "v3.9.7"
    # setup CoG environment
    esg_bash2py.mkdir_p(COG_DIR)

    COG_CONFIG_DIR = "{COG_DIR}/cog_config".format(COG_DIR=COG_DIR)
    esg_bash2py.mkdir_p(COG_CONFIG_DIR)

    COG_INSTALL_DIR= "{COG_DIR}/cog_install".format(COG_DIR=COG_DIR)
    esg_bash2py.mkdir_p(COG_INSTALL_DIR)

    os.environ["LD_LIBRARY_PATH"] = "/usr/local/lib"
    try:
        clone_cog_repo(COG_INSTALL_DIR)
    except GitCommandError, error:
        logger.exception("Failed to clone COG repo: \n %s", error)

    # install CoG dependencies
    with esg_bash2py.pushd(COG_INSTALL_DIR):
        # "pip install -r requirements.txt"
        with open("requirements.txt", "r") as req_file:
            requirements = req_file.readlines()
        for req in requirements:
            pip.main(["install", req.strip()])

        # esg_functions.stream_subprocess_output("pip install -r requirements.txt")
        # setup CoG database and configuration
        esg_functions.stream_subprocess_output("python setup.py install")
        # manually install additional dependencies
        transfer_api_client_python(os.path.join(COG_DIR, "transfer-api-client-python"))

        setup_django_openid_auth(os.path.join(COG_DIR, "django-openid-auth"))

        # create or upgrade CoG installation
        esg_functions.stream_subprocess_output("python setup.py setup_cog --esgf=true")

        # collect static files to ./static directory
        # must use a minimal settings file (configured with sqllite3 database)
        shutil.copyfile(os.path.join(current_directory, "cog_conf/cog_settings.cfg"), "{COG_DIR}/cog_config/cog_settings.cfg".format(COG_DIR=COG_DIR))
        esg_functions.stream_subprocess_output("python manage.py collectstatic --no-input")
        os.remove("{COG_DIR}/cog_config/cog_settings.cfg".format(COG_DIR=COG_DIR))

    # create non-privileged user to run django
    esg_functions.stream_subprocess_output("groupadd -r cogadmin")
    esg_functions.stream_subprocess_output("useradd -r -g cogadmin cogadmin")
    esg_bash2py.mkdir_p("~cogadmin")
    esg_functions.stream_subprocess_output("chown cogadmin:cogadmin ~cogadmin")

    # change user prompt
    with open("~cogadmin/.bashrc", "a") as cogadmin_bashrc:
        cogadmin_bashrc.write('export PS1="[\u@\h]\$ "')

    change_cog_dir_owner(COG_DIR, COG_CONFIG_DIR)

    # startup
    shutil.copyfile(os.path.join(current_directory, "cog_scripts/wait_for_postgres.sh"), "/usr/local/bin/wait_for_postgres.sh")
    shutil.copyfile(os.path.join(current_directory, "cog_scripts/process_esgf_config_archive.sh"), "/usr/local/bin/process_esgf_config_archive.sh")

def main():
    setup_cog()

if __name__ == '__main__':
    main()
