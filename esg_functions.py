#!/usr/bin/local/env python

import sys
import os
import subprocess
import re
import math

esg_functions_file = "/Users/hill119/Development/esgf-installer/esg-functions"
esg_init_file="/Users/hill119/Development/esgf-installer/esg-init"

def print_hello():
	print "hello world"


subprocess.call(['ls', '-1'], shell=True)
subprocess.call('echo $HOME', shell=True)
subprocess.check_call('echo $PATH', shell=True)


def checked_done():
	'''
		if positional parameter at position 1 is non-zero, then print error message.
	'''
	print "sys.argv[1]: ", sys.argv[1]
	print "type: ", type(sys.argv[1]) 
	if int(sys.argv[1]) != 0:
		print (
			""
        "Sorry... \n"
        "This action did not complete successfully\n"
        "Please re-run this task until successful before continuing further\n"
        ""
        "Also please review the installation FAQ it may assist you\n"
        "https://github.com/ESGF/esgf.github.io/wiki/ESGFNode%7CFAQ"
        ""
        )
	else:
		return 0


def version_comp(test1, test2):
	'''
		Takes two strings, splits them into epoch (before the last ':'),
		version (between the last ':' and the first '-'), and release
		(after the first '-'), and then calls _version_segment_cmp on
		each part until a difference is found.
		
		Empty segments are replaced with "-1" so that an empty segment
		can precede a non-empty segment when being passed to
		_version_segment_cmp.  As with _version_segment_cmp, leading
		zeroes will likely confuse comparison as this is still
		fundamentally a string sort to allow strings like "3.0alpha1".
		
		If $1 > $2, prints 1.  If $1 < $2, prints -1.  If $1 = $2, prints 0.
		Usage example:
		  if [ "$(_version_cmp $MYVERSION 1:2.3.4-5)" -lt 0 ] ; then ...
	 '''
	print "test: ", test1
	version1 = re.search(r'(.*):(.*)-(\w)', test1)
	if (version1):
		epoch_a = version1.group(1)
	else:
		epoch_a = -1	
	# print "version1:", version1.groups()
	
	# epoch_a = re.search( r'(.*):.*', test1).group(0)
	print "epoch_a: ", epoch_a

	non_epoch_a = re.search(r'(?:.*:)?(.*)', test1).group(0)
	# non_epoch_a = re.search( r':(.+)-(\w)', test)
	print "non_epoch_a: ", non_epoch_a

	version_a = re.search(r'([^-]*)', test1).group(1)
	# version_a = version1.group(2)
	print "version_a: ", version_a

	# release_a = version1.group(3)
	release_a = re.search(r'[^-]*-(.*)', test1)
	if (release_a):
		release_a = release_a.group(1)
	else:
		release_a = -1
	print "release_a: ", release_a

	version2 = re.search(r'(.*):(.*)-(\w)', test2)
	# print "version2:", version2.groups()

	if (version2):
		epoch_b = version2.group(1)
	else:
		epoch_b = -1
	# epoch_b = re.search( r'(.*):.*', test2).group(0)
	print "epoch_b: ", epoch_b

	non_epoch_b = re.search(r'(?:.*:)?(.*)', test2).group(0)
	# non_epoch_b = re.search( r':(.+)-(\w)', test2)
	print "non_epoch_b: ", non_epoch_b

	version_b = re.search(r'([^-]*)', test2).group(1)
	print "version_b: ", version_b

	release_b = re.search(r'[^-]*-(.*)', test2)
	if (release_b):
		release_b = release_b.group(1)
	else:
		release_b = -1
	print "release_b: ", release_b

	# comp_list = []
	epoch_comp = version_segment_comp(str(epoch_a), str(epoch_b))
	version_comp = version_segment_comp(str(version_a), str(version_b))
	release_comp = version_segment_comp(str(release_a), str(release_b))
	comp_list = [epoch_comp, version_comp, release_comp]
	# comp_list.extend(epoch_comp, version_comp, release_comp)
	for comp_value in comp_list:
		print "comp_value: ", comp_value
		if (comp_value != 0):
			return comp_value
	return 0

	# if (epoch_comp == 0 ):
	# 	return epoch_comp
	# else: 
	# 	if (version_segment_comp(version_a, version_b) != 0):
	# 		return version_segment_comp(version_a, version_b)
	# 	if(version_segment_comp(release_a, release_b) !=0):
	# 		return version_segment_comp(release_a, release_b)
	# 	else: 
	# 		return 0





def version_segment_comp(test1, test2):
	'''
		Takes two strings, splits them on each '.' into arrays, compares
		array elements until a difference is found.
		
		If a third argument is specified, it will override the separator
		'.' with whatever characters were specified.
		
		This doesn't take into account epoch or release strings (":" or
		"-" segments).  If you want to compare versions in the format of
		"1:2.3-4", use _version_cmp(), which calls this function.
		
		If the values for both array elements are purely numeric, a
		numeric compare is done (to handle problems such as 9 > 10 or
		02 < 1 in a string compare), but if either value contains a
		non-numeric value or is null a string compare is done.  Null
		values are considered less than zero.
		
		If $1 > $2, prints 1.  If $1 < $2, prints -1.  If $1 = $2, prints 0.
		
		Usage example:
		  if [ "$(_version_segment_cmp $MYVERSION 1.2.3)" -lt 0 ] ; then ...
	  '''
	print "test: ", test1
	# testing = re.search(r'\.', test)
	# print "testing: ", testing.group(0)
	version1 = re.sub(r'\.', r' ', test1)
	version1 = version1.split()
	print "version 1: ", version1
	print "version 1 type: ", type(version1)

	version2 = re.sub(r'\.', r' ', test2)
	version2 = version2.split()
	print "version 2: ", version2
	print "version 2 type: ", type(version2)

	version_length = max(len(version1), len(version2))
	print "version_length: ", version_length

	for i in range(version_length):
		if ( not version1[i].isdigit() or not version2[i].isdigit()):
			print "making non-numeric comparison"
			if (version1[i].lower() == version2[i].lower()):
				return 0
			elif (version1[i].lower() > version2[i].lower()):
				# return "version 1 is newer"
				return 1
			else:
				# return "version 2 is newer"
				return -1
		else:
			if (version1[i] == version2[i]):
				return 0
			if (version1[i] > version2[i]):
				# return "version 1 is newer (numeric)"
				return 1
			else:
				# return "version 2 is newer (numeric)"
				return -1

def check_version_atleast(version1, version2):
	'''
		Takes the following arguments:
		  $1: a string containing the version to test
		  $2: the minimum acceptable version
		
		Returns 0 if the first argument is greater than or equal to the
		second and 1 otherwise.
		
		Returns 255 if called with less than two arguments.
	'''
	if (version_comp(version1, version2) >= 0):
		return 0
	else:
		return 1

# checked_done()
# print version_comp("2:2.3.4-5", "3:2.5.3-1")
# check = version_segment_comp("2.3.4", "3.2.5")
# print "check: ", check