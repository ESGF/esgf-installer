'''Module for setting up the CoG Django app'''
import os
import logging
import ConfigParser
from git import Repo, GitCommandError
from esgf_utilities import esg_functions
from esgf_utilities import pybash
from esgf_utilities import esg_property_manager
from plumbum.commands import ProcessExecutionError


LOGGER = logging.getLogger("esgf_logger" +"."+ __name__)


#TODO: This is duplicating checkout_publisher_branch in esg_publisher; Should be generalized
def checkout_cog_branch(cog_path, branch_name):
    '''Checkout a given branch of the COG repo'''
    publisher_repo_local = Repo(cog_path)
    publisher_repo_local.git.checkout(branch_name)
    return publisher_repo_local

def clone_cog_repo(cog_install_dir, cog_tag="master"):
    '''Clone the COG repo from Github'''
    print "\n*******************************"
    print "Cloning COG repo"
    print "******************************* \n"

    from git import RemoteProgress
    class Progress(RemoteProgress):
        '''Prints progress of cloning from Github'''
        def update(self, op_code, cur_count, max_count=None, message=''):
            if message:
                print 'Downloading: (==== {} ====)\r'.format(message)
                print "current line:", self._cur_line

    # Repo.clone_from("https://github.com/EarthSystemCoG/COG.git", cog_install_dir, progress=Progress())
    Repo.clone_from("https://github.com/William-Hill/COG.git", cog_install_dir, progress=Progress())
    # checkout_cog_branch(cog_install_dir, cog_tag)
    checkout_cog_branch(cog_install_dir, "ESGF_3.0")

def transfer_api_client_python(target_directory):
    '''Clones and setups up the Transfer API Client'''
    print "\n*******************************"
    print "Setting up Transfer API Client"
    print "******************************* \n"
    if os.path.isdir(target_directory):
        LOGGER.info("target_directory %s already exists. Skipping cloning from Github", target_directory)
    else:
        Repo.clone_from("https://github.com/globusonline/transfer-api-client-python.git", target_directory)
    with pybash.pushd(target_directory):
        repo = Repo(os.path.join(target_directory))
        git = repo.git
        git.pull()
        with pybash.pushd("mkproxy"):
            esg_functions.call_binary("make", ["install"])

def change_cog_dir_owner(cog_dir, cog_config_dir):
    '''Change ownership of cog_config_dir/site_media'''
    apache_user = esg_functions.get_user_id("apache")
    apache_group = esg_functions.get_group_id("apache")
    esg_functions.change_ownership_recursive("{cog_dir}".format(cog_dir=cog_dir), apache_user, apache_group)
    esg_functions.change_ownership_recursive("{cog_config_dir}".format(cog_config_dir=cog_config_dir), apache_user, apache_group)

    # # create location where Python eggs can be unpacked by user 'apache'
    python_egg_cache_dir = "/var/www/.python-eggs"
    esg_functions.change_ownership_recursive("{python_egg_cache_dir}".format(python_egg_cache_dir=python_egg_cache_dir), apache_user, apache_group)

def setup_cog(cog_dir="/usr/local/cog"):
    '''Sets up the CoG Django app'''
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
    cog_tag = "v3.10.1"
    # setup CoG environment
    pybash.mkdir_p(cog_dir)

    cog_config_dir = "{cog_dir}/cog_config".format(cog_dir=cog_dir)
    pybash.mkdir_p(cog_config_dir)

    cog_install_dir = "{cog_dir}/cog_install".format(cog_dir=cog_dir)
    pybash.mkdir_p(cog_install_dir)

    os.environ["LD_LIBRARY_PATH"] = "/usr/local/lib"
    try:
        clone_cog_repo(cog_install_dir, cog_tag)
    except GitCommandError, error:
        LOGGER.exception("Failed to clone COG repo: \n %s", error)

    # XXX The git url for django openid auth is a fork at v0.7
    #  of the real project. The real project is now at v0.14,
    #  but has very little development currently
    esg_functions.pip_install_git(
        "https://github.com/EarthSystemCoG/django-openid-auth.git",
        "django-openid-auth"
    )
    # install CoG dependencies
    with pybash.pushd(cog_install_dir):
        # "pip install -r requirements.txt"
        esg_functions.pip_install("requirements.txt", req_file=True)

        # Build and install mkproxy
        transfer_api_client_python(os.path.join(cog_dir, "transfer-api-client-python"))

        # setup CoG database and configuration
        esg_functions.call_binary("python", ["setup.py", "install"])

        # create or upgrade CoG installation
        esg_functions.call_binary("python", ["setup.py", "setup_cog", "--esgf=true"])

        # collect static files to ./static directory
        esg_functions.call_binary("python", ["manage.py", "collectstatic", "--no-input"])

    # create non-privileged user to run django
    esg_functions.add_unix_group("cogadmin")
    try:
        esg_functions.call_binary("useradd", ["-r", "-g", "cogadmin", "cogadmin"])
    except ProcessExecutionError, err:
        if err.retcode == 9:
            pass
        else:
            raise

    pybash.mkdir_p("~cogadmin")
    esg_functions.call_binary("chown", ["cogadmin:cogadmin", "~cogadmin"])

    # change user prompt
    with open("~cogadmin/.bashrc", "a") as cogadmin_bashrc:
        cogadmin_bashrc.write('export PS1="[\u@\h]\$ "')

    change_cog_dir_owner(cog_dir, cog_config_dir)

def main():
    '''Main function'''
    setup_cog()

if __name__ == '__main__':
    main()
