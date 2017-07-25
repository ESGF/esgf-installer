""" Place Holder..."""
import os
import re
import sys
import hashlib
import shutil
import requests
import esg_bash2py


devel = "0"
install_prefix = os.path.join("usr", "local")
script_maj_version = "2.0"
esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"


def setup_dir():
    """ Setup main directory."""
    # directory path
    script_install_dir = os.path.join(install_prefix, "bin")
    # create directory
    os.mkdir(script_install_dir)
    # script path
    init_scripts_dir = os.path.join("etc", "rc.d", "init.d")
    # get current working directory
    starting_directory = os.getcwd()
    # change to script path
    os.chdir(script_install_dir)
    # return the location of the scripts
    return (init_scripts_dir, starting_directory, script_install_dir)


def check_for_root_id():
    '''Checks to see if the user is currently root'''
    root_id = os.geteuid()
    if root_id != 0:
        print "$([FAIL]) \n\tMust run this program with root's effective UID\n\n"
        return 1
    return 0


def confirm_file_status(return_value, fetch_file, starting_directory):
    """ Check to see if the file is Updated or needs to be installed."""
    if return_value == 1:
        print "ESGF Node install script {} already up-to-date".format(fetch_file)
    elif return_value == 0:
        print "Updated ESGF Node install script {} from ESGF distribution site".format(fetch_file)
    elif return_value > 1:
        os.chdir(starting_directory)
        return 1


def get_latest_esgf_install_scripts():
    '''
            Checks for updates to the ESGF Install Scripts; if updates
            are found download and update to latest script version
    '''
    # setup directory and location where the scripts live
    init_scripts_dir, starting_directory, script_install_dir = setup_dir()
    # variable declaration
    fetch_file = "esg_node.py"
    return_value = None

    print "Checking......"

    # check esg_node.py
    return_value = checked_get("%s/esgf-installer/%s/%s" % (esg_dist_url,
                                                            script_maj_version, re.search("^([^.]*).*", fetch_file).group(1)))
    confirm_file_status(return_value, fetch_file, starting_directory)
    os.chmod(fetch_file, 0755)
    if os.path.isfile(init_scripts_dir + "/" + fetch_file):
        shutil.copyfile(fetch_file, init_scripts_dir + "/" + fetch_file)

    # check esg_functions.py
    return_value = checked_get("%s/esgf-installer/%s/esg-functions" %
                               (esg_dist_url, script_maj_version))
    confirm_file_status(return_value, "esg_functions.py", starting_directory)
    os.chmod(script_install_dir + "/esg_functions.py", 755)

    # check esg_init.py
    return_value = checked_get("%s/esgf-installer/%s/esg-init" % (esg_dist_url, script_maj_version))
    confirm_file_status(return_value, "esg_init.py", starting_directory)
    os.chmod(script_install_dir + "/esg_init.py", 755)

    # check esg_bootstrap.py
    return_value = checked_get("%s/esgf-installer/%s/esg-bootstrap" %
                               (esg_dist_url, script_maj_version))
    confirm_file_status(return_value, "esg_bootstrap.py", starting_directory)
    os.chmod(script_install_dir + "/esg_bootstrap.py", 755)

    # check setup-autoinstall
    return_value = checked_get("%s/esgf-installer/%s/setup-autoinstall" %
                               (esg_dist_url, script_maj_version))
    confirm_file_status(return_value, "setup-autoinstall", starting_directory)
    os.chmod(script_install_dir + "/setup-autoinstall", 755)  # Double check file

    # check esg-purge.py
    return_value = checked_get("%s/esgf-installer/%s/esg-purge" %
                               (esg_dist_url, script_maj_version))
    confirm_file_status(return_value, "esg_purge.py", starting_directory)
    os.chmod(script_install_dir + "/esg_purge.py", 755)

    # check jar_security_scan.py
    return_value = checked_get("%s/esgf-installer/%s/jar_security_scan" %
                               (esg_dist_url, script_maj_version))
    confirm_file_status(return_value, "jar_security_scan.py", starting_directory)
    os.chmod(script_install_dir + "/jar_security_scan.py", 755)
    os.chdir(starting_directory)

############################################
# Utility Functions
############################################


def check_for_update(filename_1, filename_2=None):
    # local_file = None
    # remote_file = None

    if filename_2 == None:
        remote_file = filename_1
        local_file = os.path.realpath(re.search("\w+-\w+$", filename_1).group())
        local_file = local_file + ".py"
        local_file = re.sub(r'\-(?=[^-]*$)', "_", local_file)
        # print "remote_file: ", remote_file
        # print "local_file: ", local_file
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
    # print "remote_file_md5 in check_for_update: ", remote_file_md5
    local_file_md5 = None

    hasher = hashlib.md5()
    with open(local_file, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
        local_file_md5 = hasher.hexdigest()
        # print "local_file_md5 in check_for_update: ", local_file_md5

    if local_file_md5 != remote_file_md5:
        print " Update Available @ %s" % (remote_file)
        return 0
    return 1

# TODO: Split into two functions: checked_get_local and checked_get_remote
# TODO: Come up with better name than checked_get


def checked_get(file_1, file_2=None):

    if check_for_update(file_1, file_2) != 0:
        return 1

    if file_2 == None:
        remote_file = file_1
        local_file = re.search("\w+-\w+$", file_1).group()
        print "remote_file in checked_get: ", remote_file
        print "local_file in checked_get: ", local_file
    else:
        local_file = file_1
        remote_file = file_2

    if os.path.isfile(local_file):
        shutil.copyfile(local_file, local_file + ".bak")
        os.chmod(local_file + ".bak", 600)

    r = requests.get(remote_file)
    if r.status_code == requests.codes.ok:
        file = open(local_file, "w")
        file.write(r.content)
        file.close()
    else:
        print " ERROR: Problem pulling down [%s] from esg distribution site" % (remote_file)
        return 2

    remote_file_md5 = requests.get(remote_file + '.md5').content
    remote_file_md5 = remote_file_md5.split()[0].strip()
    print "remote_file_md5 in checked_get: ", remote_file_md5
    local_file_md5 = None

    hasher = hashlib.md5()
    with open(local_file, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
        local_file_md5 = hasher.hexdigest()
        print "local_file_md5 in checked_get: ", local_file_md5

    if local_file_md5 != remote_file_md5:
        print " WARNING: Could not verify this file!"
        return 3
    else:
        print "[VERIFIED]"
        return 0


def self_verify():

    python_script_name = os.path.basename(__file__)
    python_script_md5_name = re.sub(r'_', "-", python_script_name)
    print "python_script_name: ", python_script_md5_name

    remote_file_md5 = requests.get("%s/esgf-installer/%s/%s.md5" % (
        esg_dist_url, script_maj_version, re.search("^([^.]*).*", python_script_md5_name).group(1))).content
    remote_file_md5 = remote_file_md5.split()[0].strip()
    print "md5 url: ", "%s/esgf-installer/%s/%s.md5" % (esg_dist_url, script_maj_version, re.search("^([^.]*).*", python_script_md5_name).group(1))
    print "remote_file_md5: ", remote_file_md5
    local_file_md5 = None

    hasher = hashlib.md5()
    with open(python_script_name, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
        local_file_md5 = hasher.hexdigest()
        print "local_file_md5: ", local_file_md5.strip()

    if local_file_md5 != remote_file_md5:
        return 3
    else:
        print "[VERIFIED]"
        return 0


def usage():
    print '''
			usage:
        esg-bootstrap [--help]
    \n
	'''
    exit(1)

############################################
# Main
############################################


def main():

    while str(sys.argv[1]) != None:
        if str(sys.argv[1]) == "-v " or str(sys.argv[1]) == "--version":
            print '''
				Earth Systems Grid Federation (http://esgf.llnl.gov) \n
		    	ESGF Node Bootstrap Script \n

			'''
            exit(0)
        elif str(sys.argv[1]) == "--devel":
            devel = "1"
        else:
            print "Unsupported option selected: %s" % (str(sys.argv[1]))
            exit(1)

    '''
	if id_check
	then
	    (( devel == 1 )) && echo "(Setup to pull from DEVELOPMENT tree...)" && esg_dist_url=http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist$( ((devel == 1)) && echo "/devel" || echo "")
	    self_verify
	    (( $? > 0 )) && printf "WARNING: $0 could not be verified!! \n(This file, $(readlink -f ${0}), may have been tampered with or there is a newer version posted at the distribution server.\nPlease re-fetch this script.)\n\n" && exit 1
	    echo "checking for updates for the ESGF Node"
	    if (($# == 1)) && [ "$1" = "--help" ]; then
		usage
	    else
		get_latest
	    fi
	fi
	exit 0
	'''

    if check_for_root_id == 0:
        if devel == 1:
            print "(Setup to pull from DEVELOPMENT tree...)"
            esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"
            verification_result = self_verify()
            if verification_result > 0:
                print "WARNING: %s could not be verified!! \n(This file, %s, may have been tampered with or there is a newer version posted at the distribution server.\nPlease re-fetch this script.)\n\n" % (str(sys.argv[0]), os.path.realpath(str(sys.argv[0])))
                exit(1)
            print "checking for updates for the ESGF Node"
            if len(sys.argv) == 2 and sys.argv[1] == "--help":
                usage()
            else:
                get_latest_esgf_install_scripts()
    exit(0)


if __name__ == "__main__":
    main()
