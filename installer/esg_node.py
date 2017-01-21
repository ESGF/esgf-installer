import os
import subprocess
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