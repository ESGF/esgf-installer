import os
import subprocess
import requests
import pip
import hashlib
import shutil
from git import Repo
from time import sleep
import esg_functions
import esg_bash2py
import esg_functions
from esg_init import EsgInit


config = EsgInit()
# os.environ['DISCOVERONLY'] = Expand.colonMinus("DISCOVERONLY")
os.environ['LANG'] = "POSIX"
os.umask(022)

DEBUG = esg_bash2py.Expand.colonMinus("DEBUG", "0")
VERBOSE = esg_bash2py.Expand.colonMinus("VERBOSE", "0")

devel = esg_bash2py.Expand.colonMinus("devel", "0")
recommended="1"
custom="0"
use_local_files="0"

progname="esg-node"
script_version="v2.0-RC5.4.0-devel"
script_maj_version="2.0"
script_release="Centaur"
envfile="/etc/esg.env"
force_install = False
upgrade_mode = 0
esg_dist_url="http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"

#--------------
#User Defined / Settable (public)
#--------------
# install_prefix=${install_prefix:-${ESGF_INSTALL_PREFIX:-"/usr/local"}}
install_prefix = esg_bash2py.Expand.colonMinus(config.config_dictionary["install_prefix"], esg_bash2py.Expand.colonMinus("ESGF_INSTALL_PREFIX", "/usr/local"))
#--------------

os.environ['UVCDAT_ANONYMOUS_LOG'] = False

# write_java_env() {
#     ((show_summary_latch++))
#     echo "export JAVA_HOME=${java_install_dir}" >> ${envfile}
#     prefix_to_path PATH ${java_install_dir}/bin >> ${envfile}
#     dedup ${envfile} && source ${envfile}
#     return 0
# }

# def write_java_env():
# 	config.config_dictionary["show_summary_latch"]++
# 	# target = open(filename, 'w')
# 	target = open(config.config_dictionary['envfile'], 'w')
# 	target.write("export JAVA_HOME="+config.config_dictionary["java_install_dir"])

'''
	ESGCET Package (Publisher)
'''
def setup_esgcet(upgrade_mode = None):
	print "Checking for esgcet (publisher) %s " % (config.config_dictionary["esgcet_version"])
	#TODO: come up with better name
	publisher_module_check = esg_functions.check_module_version("esgcet", config.config_dictionary["esgcet_version"])


	#TODO: implement this if block
	# if os.path.isfile(config.config_dictionary["ESGINI"]):
	# 	urls_mis_match=1
	# 	# files= subprocess.Popen('ls -t | grep %s.\*.tgz | tail -n +$((%i+1)) | xargs' %(source_backup_name,int(num_of_backups)), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	# 	esgini_dburl = files= subprocess.Popen("sed -n 's@^[^#]*[ ]*dburl[ ]*=[ ]*\(.*\)$@\1@p' %s | head -n1 | sed 's@\r@@'' " %(config.config_dictionary["ESGINI"]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

	if publisher_module_check == 0 and not force_install:
		print "[OK]: Publisher already installed"
		return 0

	upgrade = upgrade_mode if upgrade_mode is not None else publisher_module_check
	
	if upgrade == 1 and not force_install:
		mode = "U"
	else:
		mode = "I"


	print '''
		*******************************
     	Setting up ESGCET Package...(%s) [%s]
     	*******************************
     ''' % (config.config_dictionary["esgcet_egg_file"], mode)

   	if mode == "U":
		if config.config_dictionary["publisher_home"] == os.environ["HOME"]+"/.esgcet":
			print "user configuration", config.config_dictionary["publisher_home"]
    	else:
    		print "system configuration", config.config_dictionary["publisher_home"]

	default_upgrade_answer = None
	if force_install:
		default_upgrade_answer = "N"
	else:
		default_upgrade_answer = "Y"

	continue_installation_answer = None

	if os.path.isfile(config.config_dictionary["publisher_home"] + "/" + config.config_dictionary["publisher_config"]):
		print "Detected an existing esgcet installation..."
		if default_upgrade_answer == "N":
			continue_installation_answer = raw_input("Do you want to continue with esgcet installation and setup? [y/N]")
		else:
			continue_installation_answer = raw_input("Do you want to continue with esgcet installation and setup? [Y/n]")
		if not continue_installation_answer.strip():
			continue_installation_answer = default_upgrade_answer

		if continue_installation_answer.lower() != "y":
			print "Skipping esgcet installation and setup - will assume esgcet is setup properly"
			return 0

	try:
		os.mkdir(config.config_dictionary["workdir"])
	except OSError, e:
		if e.errno != 17:
			raise
        sleep(1)
        pass

	print "current directory: ", os.getcwd()
	starting_directory = os.getcwd()
	'''
		curl -s -L --insecure $esg_dist_url/externals/piplist.txt|while read ln; do
	      echo "wget $esg_dist_url/externals/$ln" && wget --no-check-certificate $esg_dist_url/externals/$ln
	      diff <(md5sum ${ln} | tr -s " " | cut -d " " -f 1) <(curl -s -L --insecure $esg_dist_url/externals/${ln}.md5 | tr -s " " | cut -d " " -f 1) >& /dev/null
	      if [ $? -eq 0 ]; then
	         [OK]
	         echo "${cdat_home}/bin/pip install $ln" && ${cdat_home}/bin/pip install $ln
	      else
	         [FAIL]
	      fi
	    done
	'''
	r = requests.get(esg_dist_url+"/externals/piplist.txt")
	pip_package_list_names = r.text
	for name in pip_package_list_names:
		print "downloading %s: ", name
		r = requests.get(esg_dist_url+"/externals/"+name)
		if r.status_code == requests.codes.ok:
			hasher = hashlib.md5()
			with open(r, 'rb') as f:
				buf = f.read()
				hasher.update(buf)
				pip_download_md5 = hasher.hexdigest()
				print "pip_download_md5 in checked_get: ", pip_download_md5


		pip_package_remote_md5 = requests.get(esg_dist_url+"/externals/"+name+".md5")
		pip_package_remote_md5 = pip_package_remote_md5.split()[0].strip()
		if pip_download_md5 != pip_package_remote_md5:
			print " WARNING: Could not verify this file!" 
			print "[FAIL]"
		else:
			print "[OK]"
			pip.main(['install', name])

	#clone publisher
	publisher_git_protocol="git://"

	if force_install and os.path.isdir(config.config_dictionary["workdir"]+"esg-publisher"):
		try:
			shutil.rmtree(config.config_dictionary["workdir"]+"esg-publisher")
		except:
			print "Could not delete directory: %s" % (config.config_dictionary["workdir"]+"esg-publisher")

	if os.path.isdir(config.config_dictionary["workdir"]+"esg-publisher"):
		print "Fetching the cdat project from GIT Repo... %s" % (config.config_dictionary["publisher_repo"])
		Repo.clone_from(config.config_dictionary["publisher_repo"], config.config_dictionary["workdir"]+"esg-publisher")
		if not os.path.isdir(config.config_dictionary["workdir"]+"esg-publisher/.git"):
			publisher_git_protocol="https://"
			print "Apparently was not able to fetch from GIT repo using git protocol... trying https protocol... %s" % (publisher_git_protocol)
			Repo.clone_from(config.config_dictionary["publisher_repo_https"], config.config_dictionary["workdir"]+"esg-publisher")
			if not os.path.isdir(config.config_dictionary["workdir"]+"esg-publisher/.git"):
				print "Could not fetch from cdat's repo (with git nor https protocol)"
				esg_functions.checked_done(1)

	os.chdir(config.config_dictionary["workdir"]+"esg-publisher")
	publisher_repo_local = Repo(config.config_dictionary["workdir"]+"esg-publisher")
	#pull from remote
	publisher_repo_local.remotes.origin.pull()
	#Checkout publisher tag
	try:
		publisher_repo_local.head.reference = publisher_repo_local.tags[config.config_dictionary["publisher_tag"]]
		publisher_repo_local.head.reset(index=True, working_tree=True)
	except:
		print " WARNING: Problem with checking out publisher (esgcet) revision [%s] from repository :-(" % (config.config_dictionary["esgcet_version"])

	#install publisher
	'''
	output = subprocess.check_output(
    'echo to stdout; echo to stderr 1>&2; exit 1',
    shell=True,
    )
    '''
	installation_command = "cd src/python/esgcet; %s/bin/python setup.py install" % (config.config_dictionary["cdat_home"])
	try:
		output = subprocess.call(installation_command, shell=True)
		if output != 0:
			esg_functions.checked_done(1)
	except:
		esg_functions.checked_done(1)

	if mode == "I":
		choice = None

		while choice != 0:
			print "Would you like a \"system\" or \"user\" publisher configuration: \n"
			print "\t-------------------------------------------\n"
			print "\t*[1] : System\n"
        	print "\t [2] : User\n"
	        print "\t-------------------------------------------\n"
	        print "\t [C] : (Custom)\n"
	        print "\t-------------------------------------------\n"

	        choice = raw_input("select [1] > ")
	        if choice == 1:
	        	config.config_dictionary["publisher_home"]=config.esg_config_dir+"/esgcet"
	        elif choice == 2:
	        	config.config_dictionary["publisher_home"]=os.environ["HOME"]+"/.esgcet"
	        elif choice.lower() == "c":
	        	# input = None
	        	publisher_config_directory_input = raw_input("Please enter the desired publisher configuration directory [%s] " %  config.config_dictionary["publisher_home"])
	        	config.config_dictionary["publisher_home"] = publisher_config_directory_input
	        	publisher_config_filename_input = raw_input("Please enter the desired publisher configuration filename [%s] " % config.config_dictionary["publisher_config"])
	        	choice = "(Manual Entry)"
	        else:
	        	print "Invalid Selection %s " % (choice)

	        print "You have selected: %s" % (choice)
	        print "Publisher configuration file -> [%s/%s]" % (config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"])
	        is_correct = raw_input("Is this correct? [Y/n] ")
	        if is_correct.lower() == "n":
        		continue
	        else:
	        	break 



	

	pass


def main():
	internal_node_code_versions = {}
	test = EsgInit()
	print "install_prefix: ", test.install_prefix

	internal_node_code_versions = test.populate_internal_esgf_node_code_versions()
	print internal_node_code_versions
	print "apache_frontend_version: ", internal_node_code_versions["apache_frontend_version"]

	local_test = test.populate_external_programs_versions()
	print "local_test: ", local_test
	print "globals type: ", type(globals())
	globals().update(local_test)
	print "globals: ", globals()

	ext_script_vars = test.populate_external_script_variables()
	globals().update(ext_script_vars)
	print "globals after update: ", globals()


if __name__ == '__main__':
	main()