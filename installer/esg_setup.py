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
	pass

def check_for_my_ip():
	pass