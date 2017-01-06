import os
import re
import requests
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
 

	r = requests.get(remote_file+ '.md5')



