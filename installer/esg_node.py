import os
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
def setup_esgcet():
	print "Checking for esgcet (publisher) %s " % (config.config_dictionary["esgcet_version"])
	esg_functions.check_module_version("esgcet", config.config_dictionary["esgcet_version"])
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