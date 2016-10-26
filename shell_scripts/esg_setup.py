#!/usr/bin/local/env python

import sys
import os
import subprocess


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


subprocess.call(['ls', '-1'], shell=True)
subprocess.call('echo $HOME', shell=True)
subprocess.check_call('echo $PATH', shell=True)


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