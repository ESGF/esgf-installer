import os
import re
import requests
import hashlib
import shutil
import sys
import esg_bash2py


devel = esg_bash2py.Expand.colonMinus("devel", "0")
install_prefix = esg_bash2py.Expand.colonMinus("prefix", "/usr/local")
script_maj_version="2.0"
esg_dist_url="http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"

def check_for_root_id():
	'''
		Checks to see if the user is currently root
	'''
	root_check = os.geteuid()
	if root_check != 0:
		print "$([FAIL]) \n\tMust run this program with root's effective UID\n\n"
		return 1
	return 0

def get_latest_esgf_install_scripts():
	'''
		Checks for updates to the ESGF Install Scripts; if updates are found download and update to latest script version
	'''
	script_install_dir = install_prefix+"/bin"
	os.mkdir(script_install_dir)

	init_scripts_dir="/etc/rc.d/init.d"

	current_directory = os.getcwd()
	os.chdir(script_install_dir)

	fetch_file = "esg_node.py"

	return_value = None

	print "Checking......"






############################################
# Utility Functions
############################################
def check_for_update(filename_1, filename_2 =None):
	# local_file = None
	# remote_file = None

	if filename_2 == None:
		remote_file = filename_1
		local_file = os.path.realpath(re.search("\w+$", filename_1).group())
	else:
		local_file = filename_1
		remote_file = filename_2

	if not os.path.isfile(local_file):
		print  " WARNING: Could not find local file %s" % (local_file)
		return 0
	if not os.access(local_file, os.X_OK):
		print " WARNING: local file %s not executible" % (local_file)
		os.chmod(local_file, 0755)
 

	remote_file_md5 = requests.get(remote_file+ '.md5')
	local_file_md5 = None

	hasher = hashlib.md5()
	with open(local_file, 'rb') as f:
		buf = f.read()
		hasher.update(buf)
		local_file_md5 = hasher.hexdigest()

	if local_file_md5 != remote_file_md5:
		print " Update Available @ %s" % (remote_file)
		return 0
	return 1


def checked_get(file_1, file_2 = None):
	
	if check_for_update(file_1, file_2) != 0:
		return 1

	if file_2 == None:
		remote_file = file_1
		local_file = re.search("\w+$", file_1).group()
	else:
		local_file = file_1
		remote_file = file_2

	if os.path.isfile(local_file):
		shutil.copyfile(local_file, local_file+".bak")
		os.chmod(local_file+".bak", 600)

	r = requests.get(remote_file)
	if r.status_code == requests.codes.ok:
		file = open(local_file, "w")
		file.write(r.content)
		file.close()
	else:
		print " ERROR: Problem pulling down [%s] from esg distribution site" % (remote_file) 
		return 2

	remote_file_md5 = requests.get(remote_file+ '.md5')
	local_file_md5 = None

	hasher = hashlib.md5()
	with open(local_file, 'rb') as f:
		buf = f.read()
		hasher.update(buf)
		local_file_md5 = hasher.hexdigest()

	if local_file_md5 != remote_file_md5:
		print " WARNING: Could not verify this file!" 
		return 3
	else:
		print "[VERIFIED]"
		return 0


def self_verify():

	python_script_name = os.path.basename(__file__)

	remote_file_md5 = requests.get("esg_dist_url/esgf-installer/$script_maj_version/%s.md5" % (re.search("\w+$", python_script_name).group() ) )
	local_file_md5 = None

	hasher = hashlib.md5()
	with open(python_script_name, 'rb') as f:
		buf = f.read()
		hasher.update(buf)
		local_file_md5 = hasher.hexdigest()

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

