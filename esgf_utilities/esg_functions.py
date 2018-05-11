#!/usr/bin/local/env python
''' esg-functions: ESGF Node Application Stack Functions
    description: Installer Functions for the ESGF Node application stack
'''
import sys
import os
import subprocess
import re
import shutil
import datetime
import logging
import tarfile
import hashlib
import shlex
import socket
import errno
import pwd
import grp
import stat
import getpass
import ConfigParser
from time import sleep
from distutils.spawn import find_executable
import requests
import yaml
import netifaces
from clint.textui import progress
from lxml import etree
from esg_exceptions import UnverifiedScriptError, SubprocessError, NoNodeTypeError
import esg_bash2py
import esg_property_manager

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)


def exit_with_error(error=None):
    print(
        ""
        "Sorry... \n"
        "This action did not complete successfully\n")
    if error:
        print "The following error occurred:\n", error
    print(
        "Also please review the installation FAQ it may assist you\n"
        "https://github.com/ESGF/esgf.github.io/wiki/ESGFNode%7CFAQ"
        ""
    )
    # Move back to starting directory
    os.chdir(config["install_prefix"])
    sys.exit()

#-------------------------------
# Process checking utility functions
#-------------------------------

#----------------------------------------------------------
# Process Launching and Checking...
#----------------------------------------------------------


def get_md5sum(file_name):
    '''
        #Utility function, wraps md5sum so it may be used on either mac or
        #linux machines
    '''
    hasher = hashlib.md5()
    with open(file_name, 'rb') as file_handle:
        buf = file_handle.read()
        hasher.update(buf)
        file_name_md5 = hasher.hexdigest()
        logger.debug("local_file_md5 : %s", file_name_md5)
    return file_name_md5


def get_md5sum_password(password):
    ''' Hash a password to get it's md5 value '''
    password_hasher = hashlib.md5()
    password_hasher.update(password)
    return password_hasher.hexdigest()
#----------------------------------------------------------
# Path munging...
#----------------------------------------------------------


def path_unique(path_string=os.environ["PATH"], path_separator=":"):
    '''
        Prints a unique path string

        The first (leftmost) instance of a path entry will be the one that
        is preserved.

        If $1 is specified, it will be taken as the string to deduplicate,
        otherwise $PATH is used.

        If $2 is specified, it will be taken as the path separator, which
        otherwise defaults to ':'

    '''
    split_path = path_string.split(path_separator)
    return ":".join(sorted(set(split_path), key=split_path.index))

# TODO: Maybe move this to esg_bash2py


def readlinkf(file_name):
    '''
    This is a portable implementation of GNU's "readlink -f" in
    bash/zsh, following symlinks recursively until they end in a
    file, and will print the full dereferenced path of the specified
    file even if the file isn't a symlink.

    Loop detection exists, but only as an abort after passing a
    maximum length.
    '''
    return os.path.realpath(file_name)


#----------------------------------------------------------
# File reading and writing...
#----------------------------------------------------------


def prefix_to_path(path, prepend_value):
    '''
        Prepends path components to a variable, deduplicates the list,
        then prints to stdout the export command required to prepend
        that list to that variable.

        Takes as arguments first a variable containing a colon-separated
        path to prepend to, then a space-separated collection of paths to
        prepend -- these path components MUST NOT contain spaces.

        If insufficient arguments are present, a warning message is
        printed to stderr and nothing is printed to stdout.

        Example:
          prefix_to_path LD_LIBRARY_PATH /foo/lib /bar/lib

          Would result in the entry:
            export LD_LIBRARY_PATH=/foo/lib:/bar/lib:$LD_LIBRARY_PATH

        NOTE: In the context of system setup this is usually
              WHAT YOU WANT; that your libs are found before any user libs are

    '''
    #TODO: Use sys.path.insert
    os.environ[path] = path_unique(prepend_value) + ":" + path
    return path_unique(prepend_value) + ":" + path


def backup(path, backup_dir=config["esg_backup_dir"], num_of_backups=config["num_backups_to_keep"]):
    '''
        Given a directory the contents of the directory is backed up as a tar.gz file in
        path - a filesystem path
        backup_dir - destination directory for putting backup archive (default esg_backup_dir:-/esg/backups)
        num_of_backups - the number of backup files you wish to have present in destination directory (default num_backups_to_keep:-7)
    '''
    source_directory = readlinkf(path)
    print "Backup - Creating a backup archive of %s" % (source_directory)
    current_directory = os.getcwd()

    os.chdir(source_directory)
    esg_bash2py.mkdir_p(source_directory)

    source_backup_name = re.search("\w+$", source_directory).group()
    backup_filename = readlinkf(backup_dir) + "/" + source_backup_name + \
        "." + str(datetime.date.today()) + ".tgz"
    try:
        with tarfile.open(backup_filename, "w:gz") as tar:
            tar.add(source_directory)
    except:
        print "ERROR: Problem with creating backup archive: {backup_filename}".format(backup_filename=backup_filename)
        os.chdir(current_directory)
        return 1
    if os.path.isfile(backup_filename):
        print "Created backup: %s" % (backup_filename)
    else:
        "Could not locate backup file %s" % (backup_filename)
        os.chdir(current_directory)
        return 1

    # Cleanup
    if os.getcwd() != backup_dir:
        os.chdir(backup_dir)
    files = subprocess.Popen('ls -t | grep %s.\*.tgz | tail -n +$((%i+1)) | xargs' % (
        source_backup_name, int(num_of_backups)), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if len(files.stdout.readlines()) > 0:
        print "Tidying up a bit..."
        print "old backup files to remove: %s" % (''.join(files.stdout.readlines()))
        for file_name in files.stdout.readlines():
            os.remove(file_name)

    os.chdir(current_directory)
    return 0


# TODO: No uses found
def git_tagrelease():
    '''
        Makes a commit to the current git repository updating the
        release version string and codename, tags that commit with the
        version string, and then immediately makes another commit
        appending "-devel" to the version string.

        This is to prepare for a release merge.  Note that the tag will
        not be against the correct revision after a merge to the release
        branch if it was not a fast-forward merge, so ensure that there
        are no unmerged changes from the release branch before using.

        If that happens, delete the tag, issue a git reset --hard
        against the last commit before the tag, merge the release
        branch, and try again.

        Arguments:
        $1: the release version string (mandatory)
        $2: the release codename (optional)

        Examples:
          git-tagrelease v4.5.6 AuthenticGreekPizzaEdition
        or just
          git-tagrelease v4.5.6
    '''
    pass


def get_parent_directory(directory_path):
    return os.path.join(directory_path, os.pardir)


def is_in_git_repo(file_name):
    '''
     This determines if a specified file is in a git repository.
     This function will resolve symlinks and check for a .git
     directory in the directory of the actual file as well as its
     parent to avoid attempting to call git unless absolutely needed,
     so as to be able to detect some common cases on a system without
     git actually installed and in the path.

     Accepts as an argument the file to be checked

     Returns True if the specified file is in a git repository

     Returns False otherwise
    '''
    if not find_executable("git"):
        print "Git is not installed"
        return False

    print "DEBUG: Checking to see if %s is in a git repository..." % (file_name)
    absolute_path = readlinkf(file_name)
    one_directory_up = os.path.abspath(os.path.join(absolute_path, os.pardir))
    two_directories_up = os.path.abspath(os.path.join(one_directory_up, os.pardir))

    if not os.path.isfile(file_name):
        print "DEBUG: %s does not exist yet, allowing creation" % (file_name)
        return False

    if os.path.isdir(one_directory_up + "/.git"):
        print "%s is in a git repository" % file_name
        return True

    if os.path.isdir(two_directories_up + "/.git"):
        print "%s is in a git repository" % file_name
        return True


def check_for_update(filename_1, filename_2=None):
    '''
         Does an md5 check between local and remote resource
         returns 0 (success) iff there is no match and thus indicating that
         an update is available.
         USAGE: checked_for_update [file] http://www.foo.com/file

    '''

    if filename_2 is None:
        remote_file = filename_1
        local_file = os.path.realpath(re.search(r"\w+-\w+$", filename_1).group())
        local_file = local_file + ".py"
        local_file = re.sub(r'\-(?=[^-]*$)', "_", local_file)
    else:
        local_file = filename_1
        remote_file = filename_2

    if not os.path.isfile(local_file):
        print " WARNING: Could not find local file %s" % (local_file)
        return 0
    if not os.access(local_file, os.X_OK):
        print " WARNING: local file %s not executible" % (local_file)
        os.chmod(local_file, 0755)

    remote_file_md5 = requests.get(remote_file + '.md5').content
    remote_file_md5 = remote_file_md5.split()[0].strip()
    local_file_md5 = get_md5sum(local_file)

    if local_file_md5 != remote_file_md5:
        print " Update Available @ %s" % (remote_file)
        return 0
    return 1


def download_update(local_file, remote_file=None, force_download=False, make_backup_file=False, use_local_files=False):
    '''

    If an update is available then pull it down... then check the md5 sums again!

    Yes, this results in 3 network calls to pull down a file, but it
    saves total bandwidth and it also allows the updating from the
    network process to be cronttab-able while parsimonious with
    resources.  It is also very good practice to make sure that code
    being executed is the RIGHT code!

    The 3rd token is the "force" flag value 1|0.
    1 = do not check for update, directly go and fetch the file regardless
    0 = first check for update availability. (default)

    The 4th token is for indicated whether a backup file should be made flag value 1|0.
    1 = yes, create a .bak file if the file is already there before fetching new
    0 = no, do NOT make a .bak file even if the file is already there, overwrite it

    (When using the force flag you MUST specify the first two args!!)

    NOTE: Has multiple return values test for (( $? > 1 )) when looking or errors
       A return value of 1 only means that the file is up-to-date and there
       Is no reason to fetch it.

    USAGE: checked_get [file] http://www.foo.com/file [<1|0>] [<1|0>]

    '''

    if remote_file is None:
        remote_file = local_file
        # Get the last subpath from the absolute path
        # TODO: use esg_bash2py.trim_from_head() here
        local_file = local_file.split("/")[-1]

    logger.debug("local file : %s", local_file)
    logger.debug("remote file: %s", remote_file)

    if is_in_git_repo(local_file):
        print "%s is controlled by Git, not updating" % (local_file)
        return True

    if os.path.isfile(local_file) and use_local_files:
        print '''
            ***************************************************************************
            ALERT....
            NOT FETCHING ANY ESGF UPDATES FROM DISTRIBUTION SERVER!!!! USING LOCAL FILE
            file: %s
            ***************************************************************************\n\n
        ''' % (readlinkf(local_file))
        return True

    if not force_download:
        updates_available = check_for_update(local_file, remote_file)
        if updates_available != 0:
            logger.info("No updates available.")
            return True

    if os.path.isfile(local_file) and make_backup_file:
        create_backup_file(local_file)

    print "Fetching file from %s -to-> %s" % (remote_file, local_file)
    fetch_remote_file(local_file, remote_file)

    return verify_checksum(local_file, remote_file)


def fetch_remote_file(local_file, remote_file):
    ''' Download a remote file from a distribution mirror and write its contents to the local_file '''

    try:
        remote_file_request = requests.get(remote_file, stream=True)
        with open(local_file, "wb") as downloaded_file:
            total_length = int(remote_file_request.headers.get('content-length'))
            for chunk in progress.bar(remote_file_request.iter_content(chunk_size=1024), expected_size=(total_length / 1024) + 1):
                if chunk:
                    downloaded_file.write(chunk)
                    downloaded_file.flush()
    except requests.exceptions.RequestException, error:
        logger.exception("Could not download %s", remote_file)
        sys.exit()


def create_backup_file(file_name, backup_extension=".bak", date=str(datetime.date.today())):
    '''Create a backup of a file using the given backup extension'''
    backup_file_name = file_name + date + "."+ backup_extension
    try:
        shutil.copyfile(file_name, backup_file_name)
        os.chmod(backup_file_name, 600)
    except OSError:
        logger.exception("Could not create backup file: %s\n", backup_file_name)


def verify_checksum(local_file, remote_file):
    remote_file_md5 = requests.get(remote_file + '.md5').content
    remote_file_md5 = remote_file_md5.split()[0].strip()

    local_file_md5 = get_md5sum(local_file)

    if local_file_md5 != remote_file_md5:
        print " WARNING: Could not verify this file! %s" % (local_file)
        return False
    else:
        print "{local_file} checksum [VERIFIED]".format(local_file=local_file)
        return True


def _verify_against_mirror(esg_dist_url_root, script_maj_version):
    ''' Verify that the local script matches the remote script on the distribution mirror '''
    python_script_name = os.path.basename(__file__)
    python_script_md5_name = re.sub(r'_', "-", python_script_name)
    python_script_md5_name = re.search("\w*-\w*", python_script_md5_name)
    logger.info("python_script_name: %s", python_script_md5_name)

    remote_file_md5 = requests.get("{esg_dist_url_root}/esgf-installer/{script_maj_version}/{python_script_md5_name}.md5".format(
        esg_dist_url_root=esg_dist_url_root, script_maj_version=script_maj_version, python_script_md5_name=python_script_md5_name)).content
    remote_file_md5 = remote_file_md5.split()[0].strip()

    local_file_md5 = get_md5sum(python_script_name)

    if local_file_md5 != remote_file_md5:
        raise UnverifiedScriptError
    else:
        print "[VERIFIED]"
        return True


def stream_subprocess_output(command_string):
    ''' Print out the stdout of the subprocess in real time '''
    try:
        process = subprocess.Popen(shlex.split(command_string), stdout=subprocess.PIPE)
        with process.stdout:
            for line in iter(process.stdout.readline, b''):
                print line,
        # wait for the subprocess to exit
        process.wait()
        if process.returncode != 0:
            print "\n{command_string} process returncode:".format(command_string=command_string), process.returncode
            logger.debug("stderr %s", process.stderr)
            if process.stderr:
                raise SubprocessError({"error": process.stderr, "returncode": process.returncode})
            else:
                raise SubprocessError({"error": process.stdout, "returncode": process.returncode})
    except (OSError, ValueError), error:
        print "Could not stream subprocess output"
        print "stream_subprocess_output error:", error
        raise
        exit_with_error(error)


def call_subprocess(command_string, command_stdin=None):
    ''' Mimics subprocess.call; Need this on CentOS 6 because system Python is 2.6, which doesn't have subprocess.call() '''
    logger.debug("command_string: %s", command_string)
    try:
        command_process = subprocess.Popen(shlex.split(
            command_string), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if command_stdin:
            command_process_stdout, command_process_stderr = command_process.communicate(
                input=command_stdin)
        else:
            command_process_stdout, command_process_stderr = command_process.communicate()
    except (OSError, ValueError), error:
        logger.exception("Error with subprocess")
        # exit_with_error(error)
        raise SubprocessError(error)
    else:
        logger.debug("command_process_stdout: %s", command_process_stdout)
        logger.debug("command_process_stderr: %s", command_process_stderr)
        logger.debug("command_process.returncode: %s", command_process.returncode)
        if command_process.returncode !=0:
            raise SubprocessError(command_process_stderr)
        return {"stdout": command_process_stdout, "stderr": command_process_stderr, "returncode": command_process.returncode}


def subprocess_pipe_commands(command_list):
    subprocess_list = []
    for index, command in enumerate(command_list):
        print "index:", index
        print "command:", command
        if index > 0:
            subprocess_command = subprocess.Popen(
                command, stdin=subprocess_list[index - 1].stdout, stdout=subprocess.PIPE)
            subprocess_list.append(subprocess_command)
        else:
            subprocess_command = subprocess.Popen(command, stdout=subprocess.PIPE)
            subprocess_list.append(subprocess_command)
    subprocess_list_length = len(subprocess_list)
    for index, process in enumerate(subprocess_list):
        if index != subprocess_list_length - 1:
            process.stdout.close()
        else:
            subprocess_stdout, subprocess_stderr = process.communicate()
    return subprocess_stdout


def check_shmmax(min_shmmax=48):
    '''
       NOTE: This is another **RedHat/CentOS** specialty thing (sort of)
       arg1 - min value of shmmax in MB (see: /etc/sysctl.conf)
    '''
    try:
        kernel_shmmax = esg_property_manager.get_property("kernel.shmmax")
    except ConfigParser.NoOptionError:
        pass
    set_value_mb = min_shmmax
    set_value_bytes = set_value_mb * 1024 * 1024
    cur_value_bytes = call_subprocess("sysctl -q kernel.shmmax")["stdout"].split("=")[1]
    cur_value_bytes = cur_value_bytes.strip()

    if cur_value_bytes < set_value_bytes:
        print "Current system shared mem value too low [{cur_value_bytes} bytes] changing to [{set_value_bytes} bytes]".format(cur_value_bytes=cur_value_bytes, set_value_bytes=set_value_bytes)
        call_subprocess(
            "sysctl -w kernel.shmmax={set_value_bytes}".format(set_value_bytes=set_value_bytes))
        # TODO: replace with Python to update file
        call_subprocess(
            "sed -i.bak 's/\(^[^# ]*[ ]*kernel.shmmax[ ]*=[ ]*\)\(.*\)/\1'${set_value_bytes}'/g' /etc/sysctl.conf")
        esg_property_manager.set_property("kernal_shmmax", set_value_mb)


def get_esgf_host():
    ''' Get the esgf host name from the file; if not in file, return the fully qualified domain name (FQDN) '''
    try:
        esgf_host = config["esgf_host"]
    except KeyError:
        esgf_host = socket.getfqdn()

    return esgf_host


def get_security_admin_password():
    ''' Gets the security_admin_password from the esgf_secret_file '''
    try:
        with open(config["esgf_secret_file"], 'rb') as password_file:
            security_admin_password = password_file.read().strip()
    except IOError, error:
        if error.errno == errno.ENOENT:
            logger.error("File doesn't exist %s", config["esgf_secret_file"])
        else:
            logger.exception("Could not get password from file")
    else:
        return security_admin_password


def set_security_admin_password(updated_password, password_file=config['esgf_secret_file']):
    # TODO: Rename esgf_secret_file to esgf_admin_password_file
    '''Updates the esgf_secret_file'''
    try:
        security_admin_password_file = open(password_file, 'w+')
        security_admin_password_file.write(updated_password)
    except IOError:
        logger.exception("Unable to update security_admin_password file: %s", password_file)
    finally:
        security_admin_password_file.close()

    if not get_tomcat_group_id():
        add_unix_group(config["tomcat_group"])
    tomcat_group_id = get_tomcat_group_id()

    os.chmod(config['esgf_secret_file'], 0640)
    try:
        os.chown(config['esgf_secret_file'], config[
                 "installer_uid"], tomcat_group_id)
    except OSError:
        logger.exception("Unable to change ownership of %s", password_file)

    # Use the same password when creating the postgress account and publisher accounts
    set_postgres_password(updated_password)
    set_publisher_password(updated_password)


def get_publisher_password():
    '''Gets the publisher database user's password'''
    try:
        with open(config['pub_secret_file'], "r") as secret_file:
            publisher_db_user_passwd = secret_file.read()
        return publisher_db_user_passwd
    except IOError:
        logger.exception("%s not found", config['pub_secret_file'])
        raise


def set_publisher_password(password=None):
    '''Sets the publisher database user's password; saves it to pub_secret_file
       If not password is provided as an argument, a prompt for a password is given.
    '''
    if not password:
        password_set = False
        while not password_set:
            db_user_password = getpass.getpass(
                "Enter the password for database user {db_user}: ".format(db_user=config["postgress_user"]))
            db_user_password_confirm = getpass.getpass("Re-enter the password to confirm: ")
            if confirm_password(db_user_password, db_user_password_confirm):
                password = db_user_password
                password_set = True

    try:
        with open(config['pub_secret_file'], "w") as secret_file:
            secret_file.write(password)
        print "Updated password for database {db_user}".format(db_user=config["postgress_user"])
    except IOError, error:
        logger.exception("Could not update password for %s", config["postgress_user"])
        print "error:", error
        exit_with_error(error)


def set_postgres_password(password):
    '''Updates the Postgres superuser account password; gets saved to /esg/config/.esg_pg_pass'''

    config["pg_sys_acct_passwd"] = password

    try:
        with open(config['pg_secret_file'], "w") as secret_file:
            secret_file.write(config["pg_sys_acct_passwd"])
    except IOError:
        logger.exception("Could not open %s", config['pg_secret_file'])

    os.chmod(config['pg_secret_file'], 0640)

    if not get_tomcat_group_id():
        add_unix_group(config["tomcat_group"])
    tomcat_group_id = get_tomcat_group_id()

    try:
        os.chown(config['pg_secret_file'], config[
                 "installer_uid"], tomcat_group_id)
    except OSError:
        logger.exception("Unable to change ownership of %s", config["pg_secret_file"])


def get_postgres_password():
    '''Gets the Postgres superuser account password from /esg/config/.esg_pg_pass'''
    pg_password = None
    try:
        with open(config['pg_secret_file'], "r") as secret_file:
            pg_password = secret_file.read()
    except IOError:
        logger.exception("Could not open %s", config['pg_secret_file'])

    return pg_password


def confirm_password(password_input, password_confirmation):
    '''Helper function to confirm that passwords match.
       Returns true if passwords match'''
    if password_confirmation == password_input:
        return True
    else:
        print "Sorry, values did not match"
        return False


def is_valid_password(password_input):
    if not password_input:
        print "Password cannot be blank"
        return False
    if not str.isalnum(password_input):
        print "The password can only contain alphanumeric characters"
        return False
    if len(password_input) < 6:
        print "Sorry password must be at least six characters :-( "
        return False

    return True


def set_java_keystore_password(keystore_password=None):
    '''Saves the password for a Java keystore to /esg/config/.esg_keystore_pass'''
    if not keystore_password:
        while True:
            keystore_password_input = getpass.getpass(
                "Please enter the password for this keystore: ")
            if not keystore_password_input:
                print "Invalid password. The password can not be blank."
                continue

            keystore_password_input_confirmation = getpass.getpass(
                "Please re-enter the password for this keystore: ")
            if keystore_password_input == keystore_password_input_confirmation:
                keystore_password = keystore_password_input
                break
            else:
                print "Sorry, values did not match. Please try again."
                continue

    with open(config['ks_secret_file'], 'w') as keystore_file:
        keystore_file.write(keystore_password)
    os.chmod(config['ks_secret_file'], 0640)
    os.chown(config['ks_secret_file'], get_user_id("root"), get_group_id("tomcat"))
    return True


def get_java_keystore_password():
    ''' Gets the keystore_password from the saved ks_secret_file at /esg/config/.esg_keystore_pass '''
    try:
        with open(config['ks_secret_file'], 'rb') as keystore_file:
            keystore_password = keystore_file.read().strip()
        if not keystore_password:
            set_java_keystore_password()

        with open(config['ks_secret_file'], 'rb') as keystore_file:
            keystore_password = keystore_file.read().strip()
        return keystore_password
    except IOError, error:
        if error.errno == errno.ENOENT:
            logger.info(
                "The keystore password has not been set yet so the password file %s does not exist yet.", config['ks_secret_file'])
        set_java_keystore_password()
        with open(config['ks_secret_file'], 'rb') as keystore_file:
            keystore_password = keystore_file.read().strip()
        return keystore_password


def _check_keystore_password(keystore_password):
    '''Utility function to check that a given password is valid for the global scoped {keystore_file} '''
    if not os.path.isfile(config['ks_secret_file']):
        logger.error("$([FAIL]) No keystore file present [%s]", config['ks_secret_file'])
        return False
    keystore_password = get_java_keystore_password()
    keytool_list_command = "{java_install_dir}/bin/keytool -list -keystore {keystore_file} -storepass {keystore_password}".format(
        java_install_dir=config["java_install_dir"], keystore_file=config['ks_secret_file'], keystore_password=keystore_password)
    keytool_list_process = call_subprocess(keytool_list_command)
    if keytool_list_process["returncode"] != 0:
        logger.error(
            "$([FAIL]) Could not access private keystore %s with provided password. Try again...", config['ks_secret_file'])
        return False
    return True


def verify_esg_node_script(esg_node_filename, esg_dist_url_root, script_version, script_maj_version, devel, update_action=None):
    ''' Verify the esg_node script is the most current version '''
    # Test to see if the esg-node script is currently being pulled from git, and if so skip verification
    logger.info("esg_node_filename: %s", esg_node_filename)
    if is_in_git_repo(esg_node_filename):
        logger.info("Git repository detected; not checking checksum of esg-node")
        return

    if "devel" in script_version:
        devel = True
        remote_url = "{esg_dist_url_root}/esgf-installer/{script_maj_version}".format(
            esg_dist_url_root=esg_dist_url_root, script_maj_version=script_maj_version)
    else:
        devel = False
        remote_url = "{esg_dist_url_root}/devel/esgf-installer/{script_maj_version}".format(
            esg_dist_url_root=esg_dist_url_root, script_maj_version=script_maj_version)
    try:
        _verify_against_mirror(remote_url, script_maj_version)
    except UnverifiedScriptError:
        logger.info('''WARNING: %s could not be verified!! \n(This file, %s, may have been tampered
            with or there is a newer version posted at the distribution server.
            \nPlease update this script.)\n\n''', os.path.basename(__file__), os.path.basename(__file__))

        if update_action is None:
            update_action = raw_input(
                "Do you wish to Update and exit [u], continue anyway [c] or simply exit [x]? [u/c/X]: ")

        if update_action in ["C".lower(), "Y".lower()]:
            print "Continuing..."
            return
        elif update_action in ["U".lower(), "update", "--update"]:
            print "Updating local script with script from distribution server..."

            if devel is True:
                bootstrap_path = "/usr/local/bin/esg-bootstrap --devel"
            else:
                bootstrap_path = "/usr/local/bin/esg-bootstrap"
            invoke_bootstrap = subprocess.Popen(
                bootstrap_path, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            invoke_bootstrap.communicate()

            print "Please re-run this updated script: {current_script_name}".format(current_script_name=esg_node_filename)
            sys.exit(invoke_bootstrap.returncode)
        elif update_action is "X".lower():
            print "Exiting..."
            sys.exit(1)
        else:
            print "Unknown option: {update_action} - Exiting".format(update_action=update_action)
            sys.exit(1)

    return True


def get_group_list():
    '''Returns a list of the Unix groups on the system'''
    return [group.gr_name for group in grp.getgrall()]


def get_user_list():
    '''Returns a list of the Unix users on the system'''
    return [user.pw_name for user in pwd.getpwall()]


def get_group_id(group_name):
    ''' Returns the id of the Unix group '''
    return grp.getgrnam(group_name).gr_gid


def get_user_id(user_name):
    ''' Returns the id of the Unix user '''
    return pwd.getpwnam(user_name).pw_uid


def add_group(group_name):
    '''Add a Unix user group'''
    call_subprocess("groupadd {group_name}".format(group_name=group_name))


# def add_user(user_name, sys_acct=False, comment=None, home_dir=None, groups=None, password=None, shell=None):
def add_user(name, password="", group="", full_name ="", home_dir="", shell=""):
    '''Add Unix user'''
    #check if root_user
    existing_user_ids = [user.pw_uid for user in pwd.getpwall()]
    uid = max(existing_user_ids)+1
    user_string = "{}:{}:{}:{}:{}:{}:{}".format(name,password,uid,group,full_name,home_dir,shell)

    pass


def get_tomcat_user_id():
    ''' Returns the id of the Tomcat user '''
    return pwd.getpwnam("tomcat").pw_uid


def get_tomcat_group_id():
    ''' Returns the id of the Tomcat group '''
    try:
        return grp.getgrnam("tomcat").gr_gid
    except KeyError:
        logger.exception("Could not get Tomcat group id")


def add_unix_group(group_name):
    try:
        call_subprocess("groupadd {group_name}".format(group_name=group_name))
    except Exception, error:
        print "Could not add group {group_name}".format(group_name=group_name)
        exit_with_error(error)


def add_unix_user(user_name):
    try:
        stream_subprocess_output("useradd {user_name}".format(user_name=user_name))
    except Exception, error:
        print "Could not add user {user_name}".format(user_name=user_name)
        exit_with_error(error)


def get_dir_owner_and_group(path):
    ''' Returns a tuple containing the owner and group of the given directory path '''
    stat_info = os.stat(path)
    uid = stat_info.st_uid
    gid = stat_info.st_gid
    # print uid, gid

    user = pwd.getpwuid(uid)[0]
    group = grp.getgrgid(gid)[0]
    return user, group


def track_extraction_progress(members):
    '''Output of the files being extracted from a tarball'''
    for member in members:
        # this will be the current file being extracted
        yield member


def extract_tarball(tarball_name, dest_dir="."):
    if dest_dir == ".":
        dest_dir_name = os.getcwd()
    else:
        dest_dir_name = dest_dir
    print "Extracting {tarball_name} ->  {dest_dir_name}".format(tarball_name=tarball_name, dest_dir_name=dest_dir_name)

    try:
        tar = tarfile.open(tarball_name)
        tar.extractall(dest_dir, members=track_extraction_progress(tar))
        tar.close()
    except tarfile.TarError, error:
        logger.exception("Could not extract the tarfile: %s", tarball_name)
        raise
        exit_with_error(error)


def change_ownership_recursive(directory_path, uid=-1, gid=-1):
    '''Recursively changes ownership on a directory and its subdirectories; Mimics chown -R'''
    for root, dirs, files in os.walk(readlinkf(directory_path)):
        for directory in dirs:
            os.chown(os.path.join(root, directory), uid, gid)
        for name in files:
            file_path = os.path.join(root, name)
            try:
                os.chown(file_path, uid, gid)
            except OSError:
                logger.exception("Could not change permissions on : %s", file_path)


def change_permissions_recursive(path, mode):
    '''Recursively changes permissions on a directory and its subdirectories; Mimics chmod -R'''
    for root, dirs, files in os.walk(path, topdown=False):
        for directory in [os.path.join(root, d) for d in dirs]:
            os.chmod(directory, mode)
        for file_name in [os.path.join(root, f) for f in files]:
            os.chmod(file_name, mode)


def replace_string_in_file(file_name, original_string, new_string):
    '''Goes into a file and replaces string'''
    with open(file_name, 'r') as file_handle:
        filedata = file_handle.read()
    filedata = filedata.replace(original_string, new_string)

    # Write the file out again
    with open(file_name, 'w') as file_handle:
        file_handle.write(filedata)


def get_config_ip(interface_value):
    # chain = ifconfig["eth3"] | grep["inet[^6]"] | awk['{ gsub (" *inet [^:]*:",""); print eth3}']
    #     '''
    #     #####
    #     # Get Current IP Address - Needed (at least temporarily) for Mesos Master
    #     ####
    #     Takes a single interface value
    #     "eth0" or "lo", etc...
    #     '''
    netifaces.ifaddresses(interface_value)
    ip = netifaces.ifaddresses(interface_value)[netifaces.AF_INET][0]['addr']
    return ip


def bump_git_tag(bump_level="patch", commit_message=None):
    import semver
    from git import Repo
    '''Bump the git tag version when a new release cut'''
    if not find_executable("git"):
        print "Git is not installed"
        return False

    repo = Repo(".")
    current_tag = repo.git.describe()
    if bump_level == "patch":
        semver.bump_patch(current_tag)
    if bump_level == "minor":
        semver.bump_minor(current_tag)
    if bump_level == "major":
        semver.bump_major(current_tag)
    new_tag = repo.create_tag(current_tag, message='Automatic tag "{0}"'.format(current_tag))
    repo.remotes.origin.push(new_tag)

def write_to_install_manifest(component, install_path, version, manifest_file="/esg/esgf-install-manifest"):
    # from configobj import ConfigObj
    # config = ConfigObj("/esg/esgf-install-manifest")
    # config.filename = filename
    parser = ConfigParser.SafeConfigParser()
    parser.read(manifest_file)

    try:
        # parser.add_section(datetime.date.today().strftime("%B %d, %Y"))
        parser.add_section("install_manifest")
    except ConfigParser.DuplicateSectionError:
        logger.debug("section already exists")

    parser.set("install_manifest", component, install_path + " " + version + " - " + datetime.date.today().strftime("%B %d, %Y"))
    with open(manifest_file, "w") as config_file_object:
        parser.write(config_file_object)

def get_version_from_manifest(component, manifest_file="/esg/esgf-install-manifest", section_name="install_manifest"):
    parser = ConfigParser.SafeConfigParser()
    parser.read(manifest_file)

    try:
        return parser.get(section_name, component)
    except ConfigParser.NoSectionError:
        logger.debug("could not find component %s", component)
    except ConfigParser.NoOptionError:
        logger.debug("could not find component %s", component)


def update_fileupload_jar():
    #quick-fix for removing insecure commons-fileupload jar file
    try:
        os.remove("/usr/local/solr/server/solr-webapp/webapp/WEB-INF/lib/commons-fileupload-1.2.1.jar")
    except OSError, error:
        logger.debug(error)

    try:
        os.path.isfile("/usr/local/solr/server/solr-webapp/webapp/WEB-INF/lib/commons-fileupload-1.3.2.jar")
    except OSError:
        try:
            shutil.copyfile("{tomcat_install_dir}/webapps/esg-search/WEB-INF/lib/commons-fileupload-1.3.2.jar".format(tomcat_install_dir=config["tomcat_install_dir"]), "/usr/local/solr/server/solr-webapp/webapp/WEB-INF/lib/commons-fileupload-1.3.2.jar")
        except OSError, error:
            logger.exception(error)


def update_idp_static_xml_permissions(whitelist_file_dir=config["esg_config_dir"]):
    xml_file_path = os.path.join(whitelist_file_dir, "esgf_idp_static.xml")
    current_mode = os.stat(xml_file_path)
    os.chmod(xml_file_path, current_mode.st_mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

def setup_whitelist_files(esg_dist_url_root, whitelist_file_dir=config["esg_config_dir"]):
    '''Setups up whitelist XML files from the distribution mirror'''

    print "*******************************"
    print "Setting up The ESGF whitelist files"
    print "*******************************"

    conf_file_list = ["esgf_ats.xml.tmpl", "esgf_azs.xml.tmpl", "esgf_idp.xml.tmpl"]

    apache_user_id = get_user_id("apache")
    apache_group_id = get_group_id("apache")
    for file_name in conf_file_list:
        local_file_name = file_name.split(".tmpl")[0]
        local_file_path = os.path.join(whitelist_file_dir, local_file_name)
        remote_file_url = "https://aims1.llnl.gov/esgf/dist/confs/{file_name}".format(file_name=file_name)

        download_update(local_file_path, remote_file_url)

        #replace placeholder.fqdn
        tree = etree.parse(local_file_path)
        #Had to use {http://www.esgf.org/whitelist} in search because the xml has it listed as the namespace
        if file_name == "esgf_ats.xml.tmpl":
            placeholder_string = tree.find('.//{http://www.esgf.org/whitelist}attribute').get("attributeService")
            updated_string = placeholder_string.replace("placeholder.fqdn", "esgf-dev2.llnl.gov")
            tree.find('.//{http://www.esgf.org/whitelist}attribute').set("attributeService", updated_string)
        else:
            updated_string = tree.find('.//{http://www.esgf.org/whitelist}value').text.replace("placeholder.fqdn", "esgf-dev2.llnl.gov")
            tree.find('.//{http://www.esgf.org/whitelist}value').text = updated_string
        tree.write(local_file_path)

        os.chown(local_file_path, apache_user_id, apache_group_id)
        current_mode = os.stat(local_file_path)
        #add read permissions to all, i.e. chmod a+r
        os.chmod(local_file_path, current_mode.st_mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    # update_idp_static_xml_permissions(whitelist_file_dir)



def get_node_type(config_file=config["esg_config_type_file"]):
    '''
        Helper method for reading the last state of node type config from config dir file "config_type"
        Every successful, explicit call to --type|-t gets recorded in the "config_type" file
        If the configuration type is not explicity set the value is read from this file.
    '''
    try:
        last_config_type = open(config_file, "r")
        node_type_list = last_config_type.read().split()
        if node_type_list:
            return node_type_list
        else:
            raise NoNodeTypeError
    except IOError:
        raise NoNodeTypeError
    except NoNodeTypeError:
        logger.exception('''No node type selected nor available! \n Consult usage with --help flag... look for the \"--type\" flag
        \n(must come BEFORE \"[start|stop|restart|update]\" args)\n\n''')
        sys.exit(1)


def esgf_node_info():
    '''Print basic info about ESGF installation'''
    with open(os.path.join(os.path.dirname(__file__), 'docs', 'esgf_node_info.txt'), 'r') as info_file:
        print info_file.read()

def main():
    import esg_logging_manager

    esg_logging_manager.main()
    logger = logging.getLogger("esgf_logger" + "." + __name__)

    with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
        config = yaml.load(config_file)


if __name__ == '__main__':
    main()
