#!/usr/bin/local/env python

import sys
import os
import subprocess
import pwd
import re
# import math
# import pylint
import mmap
import shutil
from OpenSSL import crypto
import datetime
import tarfile
import requests
import stat
import socket
import platform
import yum
from time import sleep
from esg_init import EsgInit
import esg_bash2py
import esg_functions

config = EsgInit()

def source(script, update=1):
    pipe = subprocess.Popen(". %s; env" % script, stdout=subprocess.PIPE, shell=True)
    data = pipe.communicate()[0]

    env = dict((line.split("=", 1) for line in data.splitlines()))
    if update:
        os.environ.update(env)

    return env


# esg_functions_file = "/usr/local/bin/esg-functions"
esg_functions_file = "/Users/hill119/Development/esgf-installer/esg-functions"
esg_init_file="/Users/hill119/Development/esgf-installer/esg-init"

def print_hello():
	print "hello world"


# subprocess.call(['ls', '-1'], shell=True)
# subprocess.call('echo $HOME', shell=True)
# subprocess.check_call('echo $PATH', shell=True)


output = subprocess.check_output(['ls', '-1'])
print 'Have %d bytes in output' % len(output)
print output

if os.path.isfile(esg_functions_file):
	print "found file: ", esg_functions_file
	# subprocess.call('source ${esg_functions_file}', shell=True)
	source(esg_init_file)
	source(esg_functions_file)
	print "sourcing from:", esg_functions_file
	print "Checking for java >= ${java_min_version} and valid JAVA_HOME... "
else:
	print "file not found"


def init_structure():

	# print "init_structure: esg_dist_url =",  config.config_dictionary["esg_dist_url"]
	config_check = 8
	directories_to_check = [config.config_dictionary["scripts_dir"], config.config_dictionary["esg_backup_dir"], config.config_dictionary["esg_tools_dir"], 
		config.config_dictionary["esg_log_dir"], config.config_dictionary["esg_config_dir"], config.config_dictionary["esg_etc_dir"], 
		config.config_dictionary["tomcat_conf_dir"], config.config_dictionary["config_file"] ]
	for directory in directories_to_check:
		if not os.path.isfile(directory):
			os.mkdir(directory)
			config_check-=1
		else:
			config_check -= 1
	if config_check != 0:
		print "ERROR: checklist incomplete $([FAIL])"
		esg_functions.checked_done(1)
	else:
		print "checklist $([OK])"

	os.chmod(config.config_dictionary["esg_etc_dir"], 0777)

	if os.access(config.envfile, os.W_OK):
		write_paths()

	#--------------
    #Setup variables....
    #--------------

	check_for_my_ip()

	if config.config_dictionary["esgf_host"]:
		esgf_host = config.config_dictionary["esgf_host"]
	else:
		esgf_host = esg_functions.get_property("esgf_host")

	if config.config_dictionary["esgf_default_peer"]:
		esgf_default_peer = config.config_dictionary["esgf_default_peer"]
	else:
		esgf_default_peer = esg_functions.get_property("esgf_default_peer")

	if config.config_dictionary["esgf_idp_peer_name"]:
		esgf_idp_peer_name = config.config_dictionary["esgf_idp_peer_name"]
	else:
		esgf_idp_peer_name = esg_functions.get_property("esgf_idp_peer_name")

	myproxy_endpoint = re.search("/\w+", source)

	if not config.config_dictionary["myproxy_port"]:
		myproxy_port =  esg_bash2py.Expand.colonMinus(esg_functions.get_property("myproxy_port"), "7512")

	if config.config_dictionary["esg_root_id"]:
		esg_root_id = config.config_dictionary["esg_root_id"]
	else:
		esg_root_id = esg_functions.get_property("esg_root_id")

	if config.config_dictionary["node_peer_group"]:
		node_peer_group = config.config_dictionary["node_peer_group"]
	else:
		node_peer_group = esg_functions.get_property("node_peer_group")

	if not config.config_dictionary["node_short_name"]:
		node_short_name = esg_functions.get_property("node_short_name")

	#NOTE: Calls to get_property must be made AFTER we touch the file ${config_file} to make sure it exists
    #this is actually an issue with dedup_properties that gets called in the get_property function

    #Get the distinguished name from environment... if not, then esgf.properties... and finally this can be overwritten by the --dname option
    #Here node_dn is written in the /XX=yy/AAA=bb (macro->micro) scheme.
    #We transform it to dname which is written in the java style AAA=bb, XX=yy (micro->macro) scheme using "standard2java_dn" function

	if config.config_dictionary["dname"]:
		dname = config.config_dictionary["dname"]
   	else:
   		dname = esg_functions.get_property("dname")

   	if config.config_dictionary["gridftp_config"]:
   		gridftp_config = config.config_dictionary["gridftp_config"]
   	else:
   		gridftp_config = esg_functions.get_property("gridftp_config", "bdm end-user")

   	if config.config_dictionary["publisher_config"]:
   		publisher_config = config.config_dictionary["publisher_config"]
   	else:
   		publisher_config = esg_functions.get_property("publisher_config", "esg.ini")

   	if config.config_dictionary["publisher_home"]:
   		publisher_home = config.config_dictionary["publisher_home"]
   	else:
   		publisher_home = esg_functions.get_property("publisher_home", config.config_dictionary["esg_config_dir"]+"/esgcet")

   	# Sites can override default keystore_alias in esgf.properties (keystore.alias=)
   	config.config_dictionary["keystore_alias"] = esg_functions.get_property("keystore_alias")

   	config.config_dictionary["ESGINI"] = publisher_home+"/"+publisher_config

   	return 0


def write_paths():
	config.config_dictionary["show_summary_latch"]+=1

	datafile = open(config.envfile, "a+")
	datafile.write("export ESGF_HOME="+config.config_dictionary["esg_root_dir"])
	datafile.write("export ESG_USER_HOME="+config.config_dictionary["installer_home"])
	datafile.write("export ESGF_INSTALL_WORKDIR="+config.config_dictionary["workdir"])
	datafile.write("export ESGF_INSTALL_PREFIX="+config.config_dictionary["install_prefix"])
	datafile.write("export PATH="+config.config_dictionary["myPATH"]+":"+os.environ["PATH"])
	datafile.write("export LD_LIBRARY_PATH="+config.config_dictionary["myLD_LIBRARY_PATH"]+":"+os.environ["LD_LIBRARY_PATH"])

	esg_functions.deduplicate(config.envfile)
	pass

def check_for_my_ip():
	pass

#checking for what we expect to be on the system a-priori
#that we are not going to install or be responsible for
def check_prerequisites():
	print '''
		\033[01;31m
      EEEEEEEEEEEEEEEEEEEEEE   SSSSSSSSSSSSSSS         GGGGGGGGGGGGGFFFFFFFFFFFFFFFFFFFFFF
      E::::::::::::::::::::E SS:::::::::::::::S     GGG::::::::::::GF::::::::::::::::::::F
      E::::::::::::::::::::ES:::::SSSSSS::::::S   GG:::::::::::::::GF::::::::::::::::::::F
      EE::::::EEEEEEEEE::::ES:::::S     SSSSSSS  G:::::GGGGGGGG::::GFF::::::FFFFFFFFF::::F
        E:::::E       EEEEEES:::::S             G:::::G       GGGGGG  F:::::F       FFFFFF\033[0m
    \033[01;33m    E:::::E             S:::::S            G:::::G                F:::::F
        E::::::EEEEEEEEEE    S::::SSSS         G:::::G                F::::::FFFFFFFFFF
        E:::::::::::::::E     SS::::::SSSSS    G:::::G    GGGGGGGGGG  F:::::::::::::::F
        E:::::::::::::::E       SSS::::::::SS  G:::::G    G::::::::G  F:::::::::::::::F
        E::::::EEEEEEEEEE          SSSSSS::::S G:::::G    GGGGG::::G  F::::::FFFFFFFFFF\033[0m
    \033[01;32m    E:::::E                         S:::::SG:::::G        G::::G  F:::::F
        E:::::E       EEEEEE            S:::::S G:::::G       G::::G  F:::::F
      EE::::::EEEEEEEE:::::ESSSSSSS     S:::::S  G:::::GGGGGGGG::::GFF:::::::FF
      E::::::::::::::::::::ES::::::SSSSSS:::::S   GG:::::::::::::::GF::::::::FF
      E::::::::::::::::::::ES:::::::::::::::SS      GGG::::::GGG:::GF::::::::FF
      EEEEEEEEEEEEEEEEEEEEEE SSSSSSSSSSSSSSS           GGGGGG   GGGGFFFFFFFFFFF.llnl.gov
    \033[0m
	'''

	print "Checking that you have root privs on %s... " % (socket.gethostname())
	root_check = os.geteuid()
	if root_check != 0:
		print "$([FAIL]) \n\tMust run this program with root's effective UID\n\n"
		return 1
	print "[OK]"

	#----------------------------------------
   	print "Checking requisites... "

   	 # checking for OS, architecture, distribution and version

	OS = platform.system()
   	MACHINE = platform.machine()
   	RELEASE_VERSION = re.search("(centos|redhat)-(\S*)-", platform.platform()).groups()[2]

   	if RELEASE_VERSION[0] != "6":
   		print "ESGF can only be installed on versions 6 of Red Hat, CentOS or Scientific Linux x86_64 systems" 
   		return 1



   


def setup_java():

	"Checking for java >= %s and valid JAVA_HOME... " % (config.config_dictionary["java_min_version"])
	print subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT)

	if os.path.isdir(config.config_dictionary["java_install_dir"]):
		java_version_check = esg_functions.check_version(config.config_dictionary["java_install_dir"]+"bin/java", config.config_dictionary["java_min_version"], version_command="-version")

		if java_version_check == 0:
			print "[OK]"
			return 0

	print '''*******************************
    		  Setting up Java... %s
    	 	 *******************************	
    	 ''' % (config.config_dictionary["java_min_version"])

	last_java_truststore_file = None
	default = "Y"
	dosetup = None

	if os.path.isdir(config.config_dictionary["java_install_dir"]+"bin/java"):
		print "Detected an existing java installation..."
		dosetup = raw_input("Do you want to continue with Java installation and setup? [Y/n]") or default
		if dosetup != "Y" or dosetup !="y":
			print "Skipping Java installation and setup - will assume Java is setup properly"
			return 0
	last_java_truststore_file = esg_functions._readlinkf(config.config_dictionary["truststore_file"]) 





yb=yum.YumBase()
inst = yb.rpmdb.returnPackages()
installed=[x.name for x in inst]
print "installed: ", installed

# yb.install("java")
# yb.resolveDeps()
# yb.buildTransaction()
# yb.processTransaction()

# packages=['bla1', 'bla2', 'bla3']

# for package in packages:
#         if package in installed:
#                 print('{0} is already installed'.format(package))
#         else:
#                 print('Installing {0}'.format(package))
#                 kwarg = {
#                         'name':package
#                 }
#                 yb.install(**kwarg)
#                 yb.resolveDeps()
#                 yb.buildTransaction()
#                 yb.processTransaction()

	pass
