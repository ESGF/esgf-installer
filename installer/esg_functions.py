#!/usr/bin/local/env python
''' esg-functions: ESGF Node Application Stack Functions
    description: Installer Functions for the ESGF Node application stack '''
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

config = EsgInit()
# print "config.config_dictionary: ", config.config_dictionary["tomcat_users_file"]
# esg_functions_file = "/Users/hill119/Development/esgf-installer/esg-functions"
# esg_init_file = "/Users/hill119/Development/esgf-installer/esg-init"


# subprocess.call(['ls', '-1'], shell=True)
# subprocess.call('echo $HOME', shell=True)
# subprocess.check_call('echo $PATH', shell=True)

#TODO: Come up with better function name
def checked_done(status):
    '''
            if positional parameter at position 1 is non-zero, then print error message.
    '''
    # print "sys.argv[1]: ", sys.argv[1]
    # print "type: ", type(sys.argv[1])
    if int(status) != 0:
        print(
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


def version_comp(input_version1, input_version2):
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

    version1 = re.search(r'(.*):(.*)-(\w)', input_version1)

    # TODO: replace with ternary operator
    if version1:
        # print "version1: ", version1.groups()
        epoch_a = version1.group(1)
    else:
        epoch_a = -1

    non_epoch_a = re.search(r'(?:.*:)?(.*)', input_version1).group(1)
    version_a = re.search(r'([^-]*)', non_epoch_a).group(1)
    release_a = re.search(r'[^-]*-(.*)', non_epoch_a)
    if release_a:
        release_a = release_a.group(1)
    else:
        release_a = -1

    version2 = re.search(r'(.*):(.*)-(\w)', input_version2)
    if version2:
        epoch_b = version2.group(1)
    else:
        epoch_b = -1
    non_epoch_b = re.search(r'(?:.*:)?(.*)', input_version2).group(1)

    version_b = re.search(r'([^-]*)', non_epoch_b).group(1)
    release_b = re.search(r'[^-]*-(.*)', non_epoch_b)
    if release_b:
        release_b = release_b.group(1)
    else:
        release_b = -1

    epoch_comparison = version_segment_comp(str(epoch_a), str(epoch_b))
    version_comparison = version_segment_comp(str(version_a), str(version_b))
    release_comparison = version_segment_comp(str(release_a), str(release_b))
    comp_list = [epoch_comparison, version_comparison, release_comparison]
    for comp_value in comp_list:
        if comp_value != 0:
            return comp_value
    return 0


def version_segment_comp(version1, version2):
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

    version1 = re.sub(r'\.', r' ', version1)
    version1 = version1.split()

    version2 = re.sub(r'\.', r' ', version2)
    version2 = version2.split()

    version_length = max(len(version1), len(version2))

    for i in range(version_length):
        try:
            if not version1[i].isdigit() or not version2[i].isdigit():
                if version1[i].lower() > version2[i].lower():
                    return 1
                elif version1[i].lower() < version2[i].lower():
                    return -1
            else:
                if version1[i] > version2[i]:
                    return 1
                elif version1[i] < version2[i]:
                    return -1
        except IndexError:
            if version1 > version2:
                return 1
            else:
                return 0
    else:
        return 0


def check_version_atleast(version1, version2):
    '''
            Takes the following arguments:
              $1: a string containing the version to test
              $2: the minimum acceptable version

            Returns 0 if the first argument is greater than or equal to the
            second and 1 otherwise.

            Returns 255 if called with less than two arguments.
    '''
    if version_comp(version1, version2) >= 0:
        return 0
    else:
        return 1


def check_version_helper(current_version, min_version, max_version=None):
    if not max_version:
        return check_version_atleast(current_version, min_version)
    else:
        return check_version_between(current_version, min_version, max_version)


def check_version_between(current_version, min_version, max_version):
    '''
          Takes the following arguments:
          $1: a string containing the version to test
          $2: the minimum acceptable version
          $3: the maximum acceptable version

        Returns 0 if the tested version is in the acceptable range
        (greater than or equal to the second argument, and less than or
        equal to the third), and 1 otherwise.

        Returns 255 if called with less than three arguments.
    '''
    if version_comp(current_version, min_version) >= 0 and version_comp(current_version, max_version) <= 0:
        return 0
    else:
        return 1


def check_version(binary_file_name, min_version, max_version=None, version_command = "--version"):
    '''
        This is the most commonly used "public" version checking
        routine.  It delegates to check_version_helper() for the actual
        comparison, which in turn delegates to other functions in a chain.

        Arguments:
          $1: a string containing executable to call with the argument
              "--version" or "-version" to find the version to check against
          $2: the minimum acceptable version string
          $3 (optional): the maximum acceptable version string

        Returns 0 if the detected version is within the specified
        bounds, or if there were not even two arguments passed.

        Returns 1 if the detected version is not within the specified
        bounds.

        Returns 2 if running the specified command with "--version" or
        "-version" as an argument results in an error for both
        (i.e. because the command could not be found, or because neither
                "--version" nor "-version" is a valid argument)
    '''
    found_version = subprocess.Popen(
        [binary_file_name, version_command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    found_version.wait()
    current_version = None
    version_tuple = found_version.communicate()
    found_version.wait()
    for version in version_tuple:
        version_number = re.search(r'(\d+\.+\d*\.*\d*[.-_@+#]*\d*).*', version)
        # if version_number:
        try:
            current_version = version_number.group(1)
        except AttributeError:
            print "attribute error"
            continue
        else:
            result = check_version_helper(
                current_version, min_version, max_version)
            if result is 0:
                return result
            else:
                if max_version is None:
                    print "\nThe detected version of %s %s is less than %s \n" % (binary_file_name, current_version, min_version)
                else:
                    print "\nThe detected version of %s %s is not between %s and %s \n" % (binary_file_name, current_version, min_version, max_version)
                return 1


def check_version_with(program_name, version_command, min_version, max_version=None):
    '''
        This is an alternate version of check_version() (see above)
        where the second argument specifies the entire command string with
        all arguments, pipes, etc. needed to result in a version number
        to compare.

        Arguments:
          $1: a string containing the name of the program version to
              check (this is only used in debugging output)
          $2: the complete command to be passed to eval to produce the
              version string to test
          $3: the minimum acceptable version string
          $4 (optional): the maximum acceptable version string

        Returns 0 if the detected version is within the specified
        bounds, or if at least three arguments were not passed

        Returns 1 if the detected version is not within the specified
        bounds.

        Returns 2 if running the specified command results in an error
    '''
    # print "test math version: ", math.__version__
    
    # print "pylint version:",  pylint.__version__
    command_list = version_command.split()
    found_version = subprocess.Popen(
        command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    version_tuple = found_version.communicate()
    for version in version_tuple:
        version = version.strip()
        version_number = re.search(r'(\d+\.+\d*\.*\d*[.-_@+#]*\d*).*', version)
        try:
            current_version = version_number.group(1)
        except AttributeError:
            print "attribute error"
            continue
        else:
            result = check_version_helper(
                current_version, min_version, max_version)
        if result is 0:
            return result
        else:
            if max_version is None:
                print "\nThe detected version of %s %s is less than %s \n" % (program_name, current_version, min_version)
            else:
                print "\nThe detected version of %s %s is not between %s and %s \n" % (program_name, current_version, min_version, max_version)
            return 1

def check_module_version(module_name, min_version):
    '''
        Checks the version of a given python module.

        Arguments:
        module_name: a string containing the name of a module that will have it's version checked
        min_version: the minimum acceptable version string
    '''
    try:
        module_version = __import__(module_name).__version__
    except AttributeError as e:
        print "error: ", e
    else:
        result = check_version_helper(
            module_version, min_version)
        if result is 0:
            return result
        else:
            print "\nThe detected version of %s %s is less than %s \n" % (module_name, module_version, min_version)
        return 1

        
# TODO: implement and test
def get_current_esgf_library_version(library_name):
    '''
        Some ESGF components, such as esgf-security, don't actually
        install a webapp or anything that carries an independent
        manifest or version command to check, so they must be checked
        against the ESGF install manifest instead.
    '''
    version_number = ""
    if not os.path.isfile("/esg/esgf-install-manifest"):
        return 1
    else:
        with open("/esg/esgf-install-manifest", "r") as manifest_file:
            for line in manifest_file:
                line = line.rstrip() # remove trailing whitespace such as '\n'
                version_number = re.search(r'(library)\w+', line)
        if version_number:
            print "version number: ", version_number
            return version_number
        else:
            return 1

def get_current_webapp_version(webapp_name, version_command = None):
    version_property = esg_bash2py.Expand.colonMinus(version_command, "Version")
    print "version_property: ", version_property
    reg_ex = r"^(" + re.escape(version_property) + ".*)"
    with open(config.config_dictionary["tomcat_install_dir"]+"/webapps/"+webapp_name+"/META-INF/MANIFEST.MF", "r") as manifest_file:
            for line in manifest_file:
                line = line.rstrip() # remove trailing whitespace such as '\n'
                version_number = re.search(reg_ex, line)
                if version_number != None:
                    # print "version number: ", version_number
                    name, version = version_number.group(1).split(":")
                    return version.strip()
    return 1
    # f = open(config.config_dictionary["tomcat_install_dir"]+"/webapps/"+webapp_name+"/META-INF/MANIFEST.MF")
    # s = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    # print "type(s): ", type(s)
    # if s.find(version_property) != -1:
    #     result = s.readline()
    #     print "result: ", result
    #     key, value = result.split(":")
    #     if not value:
    #         print "No version number found"
    #         return 1
    #     else:
    #         return value

    # version = subprocess.check_output("$(echo $(sed -n '/^'"+version_property+"':[ ]*\(.*\)/p'"+config.config_dictionary["tomcat_install_dir"]+"/webapps/"+webapp_name+"/META-INF/MANIFEST.MF | awk '{print $2}' | xargs 2> /dev/null))", shell=True)
    # print "version: ", version
    # if version:
    #     print "version: ", version
    #     return 0
    # else:
    #     return 1

def check_webapp_version(webapp_name, min_version, version_command=None):
    version_property = esg_bash2py.Expand.colonMinus(version_command, "Version")
    if not os.path.isdir(config.config_dictionary["tomcat_install_dir"]+"/webapps/"+webapp_name):
        print "Web Application %s is not present or cannot be detected!" % (webapp_name)
        return 2
    else:
        current_version= str(get_current_webapp_version(webapp_name,version_property)).strip()
        if not current_version: 
            print " WARNING:(2) Could not detect version of %s" % (webapp_name)
        else:
            version_comparison = check_version_helper(current_version,min_version)
            if version_comparison == 0:
                return version_comparison
            else: 
                print "\nSorry, the detected version of %s %s is older than required minimum version %s \n" % (webapp_name, current_version, min_version)
                return 1

#----------------------------------------------------------
# Environment Management Utility Functions
#----------------------------------------------------------
#TODO: Fix sed statement
def remove_env(env_name):
    print "removing %s's environment from %s" % (env_name, config.envfile)
    # target = open(config.config_dictionary["envfile"], "r+")
    # # target.write(temp)
    # target.close()
    found_in_env_file = False
    datafile = open(config.envfile, "r+")
    searchlines = datafile.readlines()
    datafile.seek(0)
    # datafile.close()
    for line in searchlines:
        if env_name not in line:
            datafile.write(line)
        else:
            found_in_env_file = True
    datafile.truncate()
    datafile.close()
    return found_in_env_file
    # subprocess.check_output("sed -i '/'${env_name}'/d' ${envfile}", shell = True)

#TODO: Fix sed statement
def remove_install_log_entry(entry):
    print "removing %s's install log entry from %s" % (entry, config.config_dictionary["install_manifest"])
    subprocess.check_output("sed -i '/[:]\?'${key}'=/d' ${install_manifest}")

#TODO: fix tac and awk statements
def deduplicate(envfile = None):
    '''
    Environment variable files of the form
    Ex: export FOOBAR=some_value
    Will have duplcate keys removed such that the
    last entry of that variable is the only one present
    in the final output.
    arg 1 - The environment file to dedup.
    '''
    infile = esg_bash2py.Expand.colonMinus(envfile, config.envfile)
    if not os.path.isfile(infile):
        print "WARNING: dedup() - unable to locate %s does it exist?" % (infile)
        return 1
    if not os.access(infile, os.W_OK):
        "WARNING: dedup() - unable to write to %s" % (infile)
        return 1
    else:
        datafile = open(infile, "r+")
        searchlines = datafile.readlines()
        print "searchlines: ", searchlines
        print "type(searchlines): ", type(searchlines)
        print "searchlines.reverse(): ", searchlines[::-1]
        datafile.seek(0)

        my_set = set()
        res = []

        for e in reversed(searchlines):
            print "e: ", e.split("=")
            key, value = e.split("=")
           # key = key.split()[1]
            print "key: ", key
            print "value: ", value
            if key not in my_set:
                res.append(key+ "=" + value)
                my_set.add(key)
        res.reverse()
        print "final res: ", res
        return 0


#TODO: fix tac and awk statements
def deduplicate_properties(envfile = None):
    # infile=${1:-${config_file}}
    infile = esg_bash2py.Expand.colonMinus(envfile, config.config_dictionary["config_file"])
    if not os.path.isfile(infile):
        print "WARNING: dedup_properties() - unable to locate %s does it exist?" % (infile)
        return 1
    if not os.access(infile, os.W_OK):
        "WARNING: dedup_properties() - unable to write to %s" % (infile)
        return 1
    else:
        datafile = open(infile, "r+")
        searchlines = datafile.readlines()
        print "searchlines: ", searchlines
        print "type(searchlines): ", type(searchlines)
        print "searchlines.reverse(): ", searchlines[::-1]
        datafile.seek(0)

        my_set = set()
        res = []

        for e in reversed(searchlines):
            print "e: ", e.split("=")
            key, value = e.split("=")
           # key = key.split()[1]
            print "key: ", key
            print "value: ", value
            if key not in my_set:
                res.append(key+ "=" + value)
                my_set.add(key)
        res.reverse()
        print "final res: ", res

        return 0
        # temp = subprocess.check_output("$(tac " + infile + " | awk 'BEGIN {FS=\"[ =]\"} !($1 in a) {a[$1];print $0}' | sort -k1,1)")
        # target = open(infile, 'w')
        # target.write(temp)
        # target.close()
        # subprocess.Popen("'$tmp' > ${infile}")

#TODO: fix awk statements
# def get_config_ip(interface_value):
#     '''
#     #####
#     # Get Current IP Address - Needed (at least temporarily) for Mesos Master
#     ####
#     Takes a single interface value
#     "eth0" or "lo", etc...
#     '''
    # return subprocess.check_output("ifconfig $1 | grep \"inet[^6]\" | awk '{ gsub (\" *inet [^:]*:\",\"\"); print $1}'")

#----------------------------------------------------------
# Tomcat Management Functions
#----------------------------------------------------------

def start_tomcat():
    pass
    status = check_tomcat_process()
    if status == 0:
        return 1
    elif status == 3:
        print "Please resolve this issue before starting tomcat!"
        checked_done(status)

    print "Starting Tomcat (jsvc)..."

    # mkdir -p ${tomcat_install_dir}/work/Catalina
    # chown -R ${tomcat_user}.${tomcat_group} ${tomcat_install_dir}/work
    # chmod 755 ${tomcat_install_dir}/work
    # chmod 755 ${tomcat_install_dir}/work/Catalina
    os.mkdir(config.config_dictionary["tomcat_install_dir"]+"/work/Catalina", 0755)
    os.chown(config.config_dictionary["tomcat_install_dir"]+"/work", pwd.getpwnam(config.config_dictionary["tomcat_user"]).pw_uid, pwd.getpwnam(config.config_dictionary["tomcat_user"]).pw_gid)
    os.chmod(config.config_dictionary["tomcat_install_dir"]+"/work", 0755)

    current_directory = os.getcwd()
    os.chdir(config.config_dictionary["tomcat_install_dir"])
    copy_result = subprocess.check_output("$(find $(readlink -f `pwd`/bin/) | grep jar | xargs | perl -pe 's/ /:/g')", shell=True)
    jsvc_launch_command=("JAVA_HOME=%s %s/bin/jsvc -Djava.awt.headless=true -Dcom.sun.enterprise.server.ss.ASQuickStartup=false" 
        "-Dcatalina.home=%s -pidfile %s -cp %s -outfile %s/logs/catalina.out" 
        "-errfile %s/logs/catalina.err "
        "-user %s %s %s -Dsun.security.ssl.allowUnsafeRenegotiation=false" 
        "-Dtds.content.root.path=%s org.apache.catalina.startup.Bootstrap") % (config.config_dictionary["java_install_dir"], config.config_dictionary["tomcat_install_dir"], config.config_dictionary["tomcat_install_dir"], config.config_dictionary["tomcat_pid_file"], copy_result, config.config_dictionary["tomcat_install_dir"], config.config_dictionary["tomcat_install_dir"], config.config_dictionary["tomcat_user"], config.config_dictionary["tomcat_opts"], config.config_dictionary["java_opts"], config.config_dictionary["thredds_content_dir"])
    # if [ $? != 0 ]; then
    #     echo " ERROR: Could not start up tomcat"
    #     tail ./logs/catalina.err
    #     popd >& /dev/null
    #     checked_done 1
    # fi
    if jsvc_launch_command != 0:
        print " ERROR: Could not start up tomcat"
        f = subprocess.Popen(['tail',"./logs/catalina.err"],\
                stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        # while True:
        #     line = f.stdout.readline()
        #     print line
        os.chdir(current_directory)
        checked_done(1)
    #Don't wait forever, but give tomcat some time before it starts
    # pcheck 10 2 1 -- check_tomcat_process
    # [ $? != 0 ] && echo "Tomcat couldn't be started."
    # sleep 2

def stop_tomcat():
    # check_tomcat_process
    # [ $? != 0 ] && return 1
    if check_tomcat_process() !=0:
        return 1

    # pushd $tomcat_install_dir >& /dev/null
    # echo
    # echo "stop tomcat: ${tomcat_install_dir}/bin/jsvc -pidfile $tomcat_pid_file -stop org.apache.catalina.startup.Bootstrap"
    # echo "(please wait)"
    current_directory = os.getcwd()
    os.chdir(config.config_dictionary["tomcat_install_dir"])
    print "stop tomcat: %s/bin/jsvc -pidfile %s -stop org.apache.catalina.startup.Bootstrap" % (config.config_dictionary["tomcat_install_dir"], config.config_dictionary["tomcat_pid_file"])
    print "(please wait)"
    sleep(1)
    status = subprocess.check_output(config.config_dictionary["tomcat_install_dir"]+"/bin/jsvc -pidfile"+ config.config_dictionary["tomcat_pid_file"] +" -stop org.apache.catalina.startup.Bootstrap")
    if status != 0:
        kill_status = 0
        print " WARNING: Unable to stop tomcat, (nicely)"
        print " Hmmm...  okay no more mr nice guy... issuing "
        print  "\"pkill -9 $(cat ${tomcat_pid_file})\""
        kill_return_code = subprocess.check_output("kill -9 $(cat ${tomcat_pid_file}) >& /dev/null")
        kill_status += kill_return_code
        if kill_status != 0:
            print "Hmmm... still could not shutdown... process may have already been stopped"
    subprocess.call("/bin/ps -elf | grep jsvc | grep -v grep")
    os.chdir(current_directory)
    return 0

#-------------------------------
# Process checking utility functions
#-------------------------------

def check_postgress_process():
    '''
        #This function "succeeds" (is true; returns 0)  if there *are* running processes found running

    '''
    status = subprocess.check_output(["/etc/init.d/postgresql", "status"])

    if "running" in status:
        return 0
    else:
        return 1


def check_esgf_httpd_process():
    status = subprocess.check_output(["service", "esgf-httpd", "status"])
    if status:
        return 0
    else: 
        return 1

def check_tomcat_process():
    if os.path.isfile(config.config_dictionary["tomcat_install_dir"]+"/conf/server.xml"):
        try:
            esgf_host_ip
        except NameError:
             esgf_host_ip = get_property("esgf_host_ip")
        ports= subprocess.check_output("$(sed -n 's/.*Connector.*port=\"\([0-9]*\)\".*/\1/p' "+config.config_dictionary["tomcat_install_dir"]+"/conf/server.xml | tr '\n' ',' | sed 's/,$//')")
        procs = subprocess.check_output("$(lsof -Pni TCP:$ports | tail -n +2 | grep LISTEN | sed -n 's/\(\*\|'"+ esgf_host_ip+ "'\)/\0/p'  | awk '{print $1}' | sort -u | xargs)")
        if not procs:
            #No process running on ports
            return 1
        procs_expression = subprocess.check_output("$(expr \"$procs\" : '.*jsvc.*')")
        if procs_expression > 0:
            print "Tomcat (jsvc) process is running... " 
            return 0
        else:
            print " WARNING: There is another process running on expected Tomcat (jsvc) ports!!!! [%s] ?? " % (procs)
            subprocess.Popen("lsof -Pni TCP:"+ports+" | tail -n +2 | grep LISTEN | sed -n 's/\(\*\|'"+esgf_host_ip+"'\)/\0/p'")
            return 3
    else:
        print " Warning Cannot find %s/conf/server.xml file!" % (config.config_dictionary["tomcat_install_dir"])
        print " Using alternative method for checking on tomcat process..."
        status_value = subprocess.check_output("$(ps -elf | grep jsvc | grep -v grep | awk ' END { print NR }')")

#----------------------------------------------------------
# Postgresql informational functions
#
# These functions require that Postgresql be already installed and
# running correctly.
#----------------------------------------------------------
# TODO: Could not find any instances of Postgres functions being used
def postgres_create_db():
    pass

def postgres_list_db_schemas():
    pass

def postgres_list_schemas_tables():
    pass

def postgres_list_dbs():
    pass

def  postgres_clean_schema_migration():
    pass

#----------------------------------------------------------
# Process Launching and Checking...
#----------------------------------------------------------
def pcheck(function_name, num_of_iterations =5, wait_time_in_seconds=1, return_on_true=1):
    '''
    This function is for repeatedly running a function until it returns
    true and/or the number of iterations have been reached.  The format of
    the args for this call are as follows:
    
    pcheck <num_of_iterations> <wait_time_in_seconds> <return_on_true> -- [function name] <args...>
    The default operation is the run the function once a scecond for 5 seconds or until it returns true
    The default value of iterations is 5
    The default value of wait time is  1 (second)
    The default value of return on true is 1 (no more iterations after function/command succeeds)
    the "--" is a literal argument that MUST precede the function or command you wish to call
    
    Ex:
    Run a function or command foo 3x waiting 2 seconds between and returning after function/command success
    pcheck 3 2 1 -- foo arg1 arg2
    Run a function or command foo using defaults
    pcheck -- foo arg1 arg2
    '''
    return_code = None
    for i in range(num_of_iterations):
        return_code = subprocess.Popen(function_name)
        if return_on_true ==1 and return_code == 0:
            print "\n%s [OK]\n" % (function_name)
            break
        sleep(wait_time_in_seconds)
    print "\n$%s [FAIL]\n" % (function_name)
    return return_code

# TODO: Not used anywhere; maybe deprecate
def md5sum_():
    '''
        #Utility function, wraps md5sum so it may be used on either mac or
        #linux machines
    '''
    pass
#----------------------------------------------------------
# Path munging...
#----------------------------------------------------------

def _path_unique(path_string = os.environ["PATH"], path_separator=":"):
    '''
        Prints a unique path string
        
        The first (leftmost) instance of a path entry will be the one that
        is preserved.
        
        If $1 is specified, it will be taken as the string to deduplicate,
        otherwise $PATH is used.
        
        If $2 is specified, it will be taken as the path separator, which
        otherwise defaults to ':'
        
    '''

    # local path_string=${1:-${PATH}}
    # local pathsep=${2:-":"}
    split_path = path_string.split(path_separator)
    return ":".join(sorted(set(split_path), key=split_path.index))

def _readlinkf(file_name):
    '''
    This is a portable implementation of GNU's "readlink -f" in
    bash/zsh, following symlinks recursively until they end in a
    file, and will print the full dereferenced path of the specified
    file even if the file isn't a symlink.
    
    Loop detection exists, but only as an abort after passing a
    maximum length.
    '''
    return os.path.realpath(file_name)


#----------------------------------------------------------
# File reading and writing...
#----------------------------------------------------------
def insert_file_at_pattern(target_file, input_file, pattern):

    print "Inserting into %s <- %s at pattern %s" % (target_file, input_file, pattern)
    infile = target_file
    filterfile = input_file
    pattern=pattern
    try:
        f=open(infile)
        s=f.read()
        f.close()
        f=open(filterfile)
        filter = f.read()
        f.close()
        s=s.replace(pattern,filter)
        f=open(infile,'w')
        f.write(s)
        f.close()
    except:
        e = sys.exc_info()[0]
        print "<p>Error: %s</p>" % e 

#----------------------------------------------------------
# Property reading and writing...
#----------------------------------------------------------
def load_properties(property_file = config.config_dictionary["config_file"]):
    '''
        Load properties from a java-style property file
        providing them as script variables in this context
        arg 1 - optional property file (default is ${config_file})
    '''
    if not os.access(property_file, os.R_OK):
        return False
    # dedup_properties ${property_file}
    deduplicate_properties(property_file)
    separator = "="
    count = 0
    with open(property_file) as f:
        for line in f:
            key,value = line.split(separator)
            # [ -z "${key}" ] && continue
            print  "loading... "
            print  "[%s] -> " % (key)
            print "[%s]" % (value)
            # eval "${key}=\"${value}\""
            count+=1
    print "Loaded (imported) %i properties from %s" % (count, property_file)
    return 0


def get_property(property_name, default_value = None):
    '''
        Gets a single property from a string arg and turns it into a shell var
        arg 1 - the string that you wish to get the property of (and make a variable)
        arg 2 - optional default value to set
    '''
    if not os.access(config.config_dictionary["config_file"], os.R_OK):
        print "Unable to read file"
        return False
    datafile = open(config.config_dictionary["config_file"], "r+")
    searchlines = datafile.readlines()
    datafile.seek(0)
    for line in searchlines:
        if property_name in line:
            print "line: ", line
            key, value = line.split("=")
            if not value and default_value:
                return default_value.strip()
            else:
                return value.strip()
    # s = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    # if s.find(property_name) != -1:
    #     result = s.readline()
    #     print "result: ", result
    #     key, value = result.split("=")
    #     if not value and default_value:
    #         return default_value
    #     else:
    #         return value
# TODO: Not used anywhere; maybe deprecate
def get_property_as():
    '''
        Gets a single property from the arg string and turns the alias into a
        shell var assigned to the value fetched.
        arg 1 - the string that you wish to get the property of (and make a variable)
        arg 2 - the alias string value of the variable you wish to create and assign
        arg 3 - the optional default value if no value is found for arg 1
    '''
    pass

def remove_property(key):
    '''
        Removes a given variable's property representation from the property file
    '''
    print "removing $1's property from %s" % (config.config_dictionary["config_file"])
    property_found = False
    datafile = open(config.config_dictionary["config_file"], "r+")
    searchlines = datafile.readlines()
    datafile.seek(0)
    # datafile.close()
    for line in searchlines:
        if key not in line:
            datafile.write(line)
        else:
            property_found = True
    datafile.truncate()
    datafile.close()
    return property_found


def write_as_property(property_name, property_value):
    '''
        Writes variable out to property file as java-stye property
        I am replacing all bash-style "_"s with java-style "."s
        arg 1 - The string of the variable you wish to write as property to property file
        arg 2 - The value to set the variable to (default: the value of arg1)
    '''
    datafile = open(config.config_dictionary["config_file"], "a+")
    searchlines = datafile.readlines()
    datafile.seek(0)
    for line in searchlines:
        if property_name in line:
            print "Property already exists"
            return "Property already exists"
    else:
        datafile.write(property_name+"="+property_value+"\n")
        return 0

# TODO: Not used anywhere; maybe deprecate
def append_to_path():
    '''
        Appends path components to a variable, deduplicates the list,
        then prints to stdout the export command required to append that
        list to that variable
        
        Takes as arguments first a variable containing a colon-separated
        path to append to, then a space-separated collection of paths to
        append -- these path components MUST NOT contain spaces.
        
        If insufficient arguments are present, a warning message is
        printed to stderr and nothing is printed to stdout.
        
        Example:
          append_to_path LD_LIBRARY_PATH /foo/lib /bar/lib
        
          Would result in the entry:
            export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/foo/lib:/bar/lib
        
        NOTE: In the context of system setup this is usually
              NOT WHAT YOU WANT - use prefix_to_path (below)
        
    '''
    pass

def prefix_to_path(path, prepend_value):
    '''
        Prepends path components to a variable, deduplicates the list,
        then prints to stdout the export command required to prepend
        that list to that variable.
        
        Takes as arguments first a variable containing a colon-separated
        path to prepend to, then a space-separated collection of paths to
        prepend -- these path components MUST NOT contain spaces.
        
        If insufficient arguments are present, a warning message is
        printed to stderr and nothing is printed to stdout.
        
        Example:
          prefix_to_path LD_LIBRARY_PATH /foo/lib /bar/lib
        
          Would result in the entry:
            export LD_LIBRARY_PATH=/foo/lib:/bar/lib:$LD_LIBRARY_PATH
        
        NOTE: In the context of system setup this is usually
              WHAT YOU WANT; that your libs are found before any user libs are
        
    '''
    os.environ[path] = _path_unique(prepend_value)+":"+path
    return _path_unique(prepend_value)+":"+path

def backup(path, backup_dir = config.config_dictionary["esg_backup_dir"], num_of_backups=config.config_dictionary["num_backups_to_keep"]):
    '''
        Given a directory the contents of the directory is backed up as a tar.gz file in
        arg1 - a filesystem path
        arg2 - destination directory for putting backup archive (default esg_backup_dir:-/esg/backups)
        arg3 - the number of backup files you wish to have present in destination directory (default num_backups_to_keep:-7)
    '''
    source = _readlinkf(path)
    print "Backup - Creating a backup archive of %s" % (source)
    current_directory = os.getcwd()
    
    os.chdir(source)
    try:
        os.mkdir(backup_dir)
    except OSError, e:
        if e.errno != 17:
            raise
        sleep(1)
        pass

    source_backup_name = re.search("\w+$", source).group()
    backup_filename=_readlinkf(backup_dir)+"/"+source_backup_name + "." + str(datetime.date.today())+".tgz"
    try:
        with tarfile.open(backup_filename, "w:gz") as tar:
            tar.add(source)
    except:
        print " ERROR: Problem with creating backup archive: ${backup_filename}"
        os.chdir(current_directory)
        return 1
    if os.path.isfile(backup_filename):
        print "Created backup: %s" % (backup_filename)
    else:
        "Could not locate backup file %s" % (backup_filename)
        os.chdir(current_directory)
        return 1


    # Cleanup
    if os.getcwd() != backup_dir:
        os.chdir(backup_dir)
    files= subprocess.Popen('ls -t | grep %s.\*.tgz | tail -n +$((%i+1)) | xargs' %(source_backup_name,int(num_of_backups)), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if len(files.stdout.readlines()) > 0:
        print "Tidying up a bit..."
        print "old backup files to remove: %s" % (''.join(files.stdout.readlines()))
        for file in files.stdout.readlines():
            os.remove(file)

    os.chdir(current_directory)
    return 0

# TODO: No uses found
def get_node_id():
    '''
        Get (or generate) the id suitable for use in the context of zookeeper
        and thus the sharded solr install.  If this variable is not set then
        an ID is generated, unique to this host.
        NOTE: A lot of things rely on this ID so at the moment it is okay to
        provide a simple way to be able to determine an id externally... but
        this is only something for the testing phase for the most part.
    '''
    pass
    
# TODO: No uses found
def git_tagrelease():
    '''
        Makes a commit to the current git repository updating the
        release version string and codename, tags that commit with the
        version string, and then immediately makes another commit
        appending "-devel" to the version string.
        
        This is to prepare for a release merge.  Note that the tag will
        not be against the correct revision after a merge to the release
        branch if it was not a fast-forward merge, so ensure that there
        are no unmerged changes from the release branch before using.
        
        If that happens, delete the tag, issue a git reset --hard
        against the last commit before the tag, merge the release
        branch, and try again.
        
        Arguments:
        $1: the release version string (mandatory)
        $2: the release codename (optional)
        
        Examples:
          git-tagrelease v4.5.6 AuthenticGreekPizzaEdition
        or just
          git-tagrelease v4.5.6
    '''
    pass

#------------------------------------------
#Certificate Gymnasitcs
#------------------------------------------
expired=0
day=60*60*24
warn=day*7
info=day*3

certs_expired = []
certs_immediate_expire = []
certs_week_expire = []
certs_month_expire = []
def print_cert(certificate_path):
    print "CERTIFICATE = %s" % (certificate_path)
    # cert_file = '/path/to/your/certificate'
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(certificate_path).read())
    print "%s  %s" % (cert.get_subject(), cert.notAfter())
    # subject = cert.get_subject()
    # issued_to = subject.CN    # the Common Name field
    # issuer = cert.get_issuer()
    # issued_by = issuer.CN 

def check_cert_expiry(certificate_path):
    
    print "inspecting %s" % (certificate_path)
    try:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(certificate_path).read())
        if cert.has_expired():
            certs_expired.append(cert)
            return
        expire_date = datetime.strptime(cert.notAfter(), "%Y%m%d%H%M%SZ")
        expire_in = expire_date - datetime.now()
        if expire_in.days < 0:
            certs_immediate_expire.append(cert)
        elif expire_in.days <= 7:
            certs_week_expire.append(cert)
        elif expire_in.days <= 30:
            certs_month_expire.append(cert)

    except:
        # exit_error(1, 'Certificate date format unknow.')
        print "Certificate date formate unknown."

def check_cert_expiry_for_files(file_path):
    print "Checking for expired certs [file(s): %s]..." % (file_path)

    # for file in $@
    # do
    #     [ ! -e "${file}" ] && echo "no such file: ${file}, skipping... " && continue
    #     check_cert_expiry ${file}
    # done
    for file in file_path:
        if not os.path.isfile(file):
            print "no such file: %s, skipping... " % (file)
            continue
        check_cert_expiry(file)

    # ocal message=
    # [ "$var_expire" ] && message=$message"Certificates will expire in:\n$var_expire\n"
    # [ "$certs_expire" ] && message=$message"Certificates already expired :\n$certs_expire\n"
    # [ "$certs_day" ] && message=$message"Certificates will expire within a day:\n$certs_day\n"
    # [ "$certs_warn" ] && message=$message"Certificates expiring this week:\n$certs_warn\n"
    # [ "$certs_info" ] && message=$message"Certificates expiring this month:\n$certs_info\n"

    # #mail -s "Certificates Expiration closes" gavin@llnl.gov < <(printf "$message")
    # printf "$message"
    print  "Certificates already expired :\n%s\n" % (certs_expired)
    print "Certificates will expire within a day:\n%s\n" % (certs_immediate_expire)
    print "Certificates expiring this week:\n%s\n" % (certs_week_expire)
    print "Certificates expiring this month:\n%s\n" % (certs_month_expire)

# TODO: No uses found
def check_certs_in_dir():
    pass

def trash_expired_cert(certificate_path):
    trash_directory = esg_bash2py.Expand.colonMinus("ESGF_PROJECT_ROOT", "/tmp")+"/trash"
    os.mkdir(trash_directory)
    shutil.move(certificate_path, trash_directory)
    print "Trashed expired certificate %s" % (certificate_path)
 

# TODO: No uses found
def set_aside_web_app():
    pass

# TODO: No uses found
def set_aside_web_app_cleanup():
    pass

#------------------------------------------
#ESGF Distribution Mirrors Utilities
#------------------------------------------

def get_esgf_dist_mirror(selection_mode, install_type = None):
    esgf_dist_mirrors_list=("distrib-coffee.ipsl.jussieu.fr/pub/esgf" "dist.ceda.ac.uk/esgf" "aims1.llnl.gov/esgf" "esg-dn2.nsc.liu.se/esgf")
    response_array = {}
    ranked_response_times = []

    # for m in "${esgf_dist_mirrors_list[@]}"; do
    #     if [ $devel -eq 1 ]; then
    #         resarray[$m]=`curl -s -L --insecure $m/dist/devel/lastpush.md5|tr -s " "|cut -d " " -f1`;
    #     else 
    #         resarray[$m]=`curl -s -L --insecure $m/dist/lastpush.md5|tr -s " "|cut -d " " -f1`;
    #     fi
    # done

    for mirror in esgf_dist_mirrors_list:
        if install_type == "devel":
            response_array[mirror] = subprocess.Popen("curl -s -L --insecure %s/dist/devel/lastpush.md5|tr -s " "|cut -d " " -f1" % (mirror), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        else:
            response_array[mirror] = subprocess.Popen("curl -s -L --insecure %s/dist/lastpush.md5|tr -s " "|cut -d " " -f1" % (mirror), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    # for m in "${esgf_dist_mirrors_list[@]}"; do

    #     # get host and page
    #     m=${m/[hH][tT][tT][pP]:\/\//}
    #     [ "${m#*\/}" == "$m" ] && page="/" || page="/${m#*\/}"
    #     host="${m%%\/*}"

    for mirror in esgf_dist_mirrors_list:
        host, page = mirror.split("/")

        #  response = requests.get('http://www.google.com')
        # >>> print response.elapsed
        # 0:00:01.762032
        # >>> response.elapsed
        # datetime.timedelta(0, 1, 762032)
        response = requests.get(host, timeout=0.001)
        ranked_response_times[mirror] = response.elapsed

    ranked_response_times.sort()

    # master=${resarray['distrib-coffee.ipsl.jussieu.fr/pub/esgf']}
    # fastest=`echo ${flist[1]}|cut -d '/' -f3-`;
    # outofsync=0
    # if [ "${resarray[$fastest]}" != "$master" ]; then #if the fastest mirror is not in sync with coffee
    #     echo "$fastest is the fastest mirror, but is out-of-sync, hence overlooked";
    #     outofsync=1;
    # fi
    master=response_array['distrib-coffee.ipsl.jussieu.fr/pub/esgf']
    fastest = ranked_response_times[0]
    outofsync=0
    if response_array[fastest] != master:
        print "%s is the fastest mirror, but is out-of-sync, hence overlooked" % fastest
        outofsync = 1
    # if [ $outofsync -eq 1 ]; then
    #     #lets use the master
    #         esgf_dist_mirror="http://distrib-coffee.ipsl.jussieu.fr/pub/esgf";
    #         #esgf_dist_mirror="http://esg-dn2.nsc.liu.se/esgf";
    #     return;
    # fi
    if outofsync == 1:
        config.config_dictionary["esgf_dist_mirror"] = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf"
        return
    # if [ -p /tmp/inputpipe ]; then
    #     echo "Using the fastest mirror (${flist[1]})";
    #     esgf_dist_mirror=${flist[1]};
    #     return;
    # fi
    if stat.S_ISFIFO(os.stat("/tmp/inputpipe").st_mode) != 0:
        print "using the fastest mirror %s" % ranked_response_times[0]
        config.config_dictionary["esgf_dist_mirror"] = ranked_response_times[0]
        return

    # if [ $1 = "interactive" ]; then
    #     i=1
    #     printf "Please select the ESGF distribution mirror for this installation (fastest to slowest): \n"
    #     printf "\t-------------------------------------------\n"
    #     for m in ${flist[@]}; do
    #         printf "\t [$i] $m \n"
    #             ((i++))
    #     done
    #     printf "\t-------------------------------------------\n"

    #     read -e -p "select [1] > " choice
    #     [ -z "${choice}" ] && choice=1

    #     echo $choice
    #     esgf_dist_mirror=${flist[$choice]}
    # else
    #     esgf_dist_mirror=${flist[1]}
    # fi
    if install_type == "interactive":
        print "\t-------------------------------------------\n"
        for index, mirror in ranked_response_times:
            print "\t %i %s" % (index, mirror)
        choice = raw_input("Please select the ESGF distribution mirror for this installation (fastest to slowest): \n")
        config.config_dictionary["esgf_dist_mirror"] = ranked_response_times[choice]
    else:
        config.config_dictionary["esgf_dist_mirror"] = ranked_response_times[0]

def is_in_git(file_name):
    '''
     This determines if a specified file is in a git repository.
     This function will resolve symlinks and check for a .git
     directory in the directory of the actual file as well as its
     parent to avoid attempting to call git unless absolutely needed,
     so as to be able to detect some common cases on a system without
     git actually installed and in the path.
    
     Accepts as an argument the file to be checked
    
     Returns 0 if the specified file is in a git repository
    
     Returns 2 if it could not detect a git repository purely by file
     position and git was not available to complete a rev-parse test
    
     Returns 1 otherwise
    '''
    # test = git.Repo("/Users/williamhill/Development/esgf-installer/installer/esg_init.py").git_dir

    '''
        debug_print "DEBUG: Checking to see if ${1} is in a git repository..."

        REALDIR=$(dirname $(_readlinkf ${1}))
    '''
    try:
        is_git_installed = subprocess.check_output(["which", "git"])
    except subprocess.CalledProcessError, e:
        print "Ping stdout output:\n", e.output
        print "git is not available to finish checking for a repository -- assuming there isn't one!"



    print "DEBUG: Checking to see if %s is in a git repository..." % (file_name)
    absolute_path = esg_functions._readlinkf(file_name)
    one_directory_up = os.path.abspath(os.path.join(absolute_path, os.pardir))
    print "absolute_path: ", absolute_path
    print "parent_path: ", os.path.abspath(os.path.join(absolute_path, os.pardir))
    two_directories_up = os.path.abspath(os.path.join(one_directory_up, os.pardir))
    print "two_directories_up: ", two_directories_up

    '''
        if [ ! -e $1 ] ; then
        debug_print "DEBUG: ${1} does not exist yet, allowing creation"
        return 1
    fi
    '''
    if not os.path.isfile(file_name):
        print "DEBUG: %s does not exist yet, allowing creation" % (file_name)
        return 1

    '''
        if [ -d "${REALDIR}/.git" ] ; then
        debug_print "DEBUG: ${1} is in a git repository"
        return 0
    fi

    '''
    if os.path.isdir(one_directory_up+"/.git"):
        print "%s is in a git repository" % file_name
        return 0

    '''
        if [ -d "${REALDIR}/../.git" ] ; then
        debug_print "DEBUG: ${1} is in a git repository"
        return 0
    fi
    '''
    if os.path.isdir(two_directories_up+"/.git"):
        print "%s is in a git repository" % file_name
        return 0



def checked_get(local_file, remote_file = None, force_get = 0, make_backup_file = 1 ):
    '''

     If an update is available then pull it down... then check the md5 sums again!
    
      Yes, this results in 3 network calls to pull down a file, but it
      saves total bandwidth and it also allows the updating from the
      network process to be cronttab-able while parsimonious with
      resources.  It is also very good practice to make sure that code
      being executed is the RIGHT code!
    
      The 3rd token is the "force" flag value 1|0.
      1 = do not check for update, directly go and fetch the file regardless
      0 = first check for update availability. (default)
    
      The 4th token is for indicated whether a backup file should be made flag value 1|0.
      1 = yes, create a .bak file if the file is already there before fetching new
      0 = no, do NOT make a .bak file even if the file is already there, overwrite it
    
      (When using the force flag you MUST specify the first two args!!)
    
     NOTE: Has multiple return values test for (( $? > 1 )) when looking or errors
           A return value of 1 only means that the file is up-to-date and there
           Is no reason to fetch it.
    
     USAGE: checked_get [file] http://www.foo.com/file [<1|0>] [<1|0>]
    
    '''

    '''
           local force_get=${3:-0}
            local make_backup_file=${4:-1} #default to make backup *.bak files if necessary

            local local_file
            local remote_file
            if (( $# == 1 )); then
                remote_file=${1}
                local_file=${1##*/}
            elif (( $# >= 2 )); then
                local_file=${1}
                remote_file=${2}
            else
                echo "function \"checked_get\":  Called with incorrect number of args! (fatal) args[$@]"
                echo " usage: checked_get [<local dest>] <remote source> [force_get (0*|1)] [make_backup_file(0|1*)]"
                exit 1
            fi
    '''
    # try:
 #      force_get = str(sys.argv[3])
    # except IndexError:
 #      force_get = '0'

 #    try:
 #      make_backup_file = str(sys.argv[4])
    # except IndexError:
 #      make_backup_file = '-1'
    # force_get = esg_bash2py.Expand.colonMinus(str(sys.argv[3]), "0")
    # make_backup_file = esg_bash2py.Expand.colonMinus(str(sys.argv[4]), "-1")
    # local_file = None
    # remote_file = None

    if remote_file == None:
        remote_file = file_1
        local_file = re.search("\w+-\w+$", file_1).group()
        print "remote_file in checked_get: ", remote_file
        print "local_file in checked_get: ", local_file

    '''
        if (_is_in_git "${local_file}") ; then
        printf "${local_file} is controlled by Git, not updating"
        return 0
    fi
    '''
    if is_in_git(local_file) == 0:
        print "%s is controlled by Git, not updating" % (local_file)

    '''
        if ((use_local_files)) && [ -e "${local_file}" ]; then
        printf "
    ***************************************************************************
    ALERT....
    NOT FETCHING ANY ESGF UPDATES FROM DISTRIBUTION SERVER!!!! USING LOCAL FILE
    file: $(readlink -f ${local_file})
    ***************************************************************************\n\n"
        return 0
    fi
    '''
    if use_local_files and if os.path.isfile(local_file):
        print '''
            ***************************************************************************
            ALERT....
            NOT FETCHING ANY ESGF UPDATES FROM DISTRIBUTION SERVER!!!! USING LOCAL FILE
            file: %s
            ***************************************************************************\n\n
        ''' % (esg_functions._readlinkf(local_file))

    '''
        if ((force_get == 0)); then
        check_for_update $@
        [ $? != 0 ] && return 1
    fi
    '''
    if force_get == 1:
        updates_available = check_for_update(local_file, remote_file)
        if updates_available != 0:
            return 1

    '''
        if [ -e ${local_file} ] && ((make_backup_file)) ; then
        cp -v ${local_file} ${local_file}.bak
        chmod 600 ${local_file}.bak
    fi
    '''
    if os.path.isfile(local_file) and make_backup_file == 1:
        shutil.copyfile(local_file, local_file+".bak")
        os.chmod(local_file+".bak", 600)

    '''
        echo "Fetching file from ${remote_file} -to-> ${local_file}"
    wget --no-check-certificate --progress=bar:force -O ${local_file} ${remote_file}
    [ $? != 0 ] && echo " ERROR: Problem pulling down [${remote_file##*/}] from esg distribution site" && return 2
    diff <(md5sum ${local_file} | tr -s " " | cut -d " " -f 1) <(curl -s -L --insecure ${remote_file}.md5 |head -1| tr -s " " | cut -d " " -f 1) >& /dev/null
    [ $? != 0 ] && echo " WARNING: Could not verify file! ${local_file}" && return 3
    echo "[VERIFIED]"
    return 0
    '''

    print "Fetching file from %s -to-> %s" % (remote_file, local_file)
    r = requests.get(remote_file)
    if not r.status_code == requests.codes.ok:
        print " ERROR: Problem pulling down [%s] from esg distribution site" % (remote_file)
        r..raise_for_status() 
        return 2
    else:
        file = open(local_file, "w")
        file.write(r.content)
        file.close()

    remote_file_md5 = requests.get(remote_file+ '.md5').content
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
        print " WARNING: Could not verify this file! %s" % (local_file)
        return 3
    else:
        print "[VERIFIED]"
        return 0



