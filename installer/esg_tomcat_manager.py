'''
Tomcat Management Functions
'''
import os
import subprocess
import sys
import hashlib
import shutil
import grp
import datetime
import socket
import re
import pwd
import tarfile
import urllib
import shlex
import filecmp
import glob
import yaml
from time import sleep
from OpenSSL import crypto
from lxml import etree
import esg_functions
import esg_bash2py
import esg_property_manager
import esg_logging_manager


logger = esg_logging_manager.create_rotating_log(__name__)

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)

def find_tomcat_ports(server_xml_path):
    '''
        Return a list of ports in the Tomcat server.xml file
    '''
    ports = []

    tree = etree.parse(server_xml_path)
    root = tree.getroot()
    port_list = root.findall(".//Connector")
    for port in port_list:
        port_number = port.get("port")
        ports.append(port_number)

    logger.debug("ports: %s", ports)
    return ports

def check_tomcat_process():
    '''
        Checks for the status of the Tomcat process
    '''
    server_xml_path = os.path.join(config["tomcat_install_dir"], "conf", "server.xml")
    logger.debug("server_xml_path: %s", server_xml_path)
    if os.path.isfile(server_xml_path):
        try:
            esgf_host_ip
        except NameError:
             esgf_host_ip = esg_property_manager.get_property("esgf_host_ip")

        ports = find_tomcat_ports(server_xml_path)

        process_list = []

        for port in ports:
            proc1 = subprocess.Popen(shlex.split('lsof -Pni TCP:{port}'.format(port = port)), stdout = subprocess.PIPE)
            proc2 = subprocess.Popen(shlex.split('tail -n +2'), stdin = proc1.stdout, stdout = subprocess.PIPE)
            proc3 = subprocess.Popen(shlex.split('grep LISTEN'), stdin = proc2.stdout, stdout = subprocess.PIPE)

            # Allow proc1 to receive a SIGPIPE if proc2 exits.
            proc1.stdout.close()
            # Allow proc2 to receive a SIGPIPE if proc3 exits.
            proc2.stdout.close()

            stdout_processes, stderr_processes = proc3.communicate()
            logger.info("port %s stdout_processes: %s", port, stdout_processes)
            logger.info("port %s stderr_processes: %s", port, stderr_processes)

            if stdout_processes:
                process_list.append(stdout_processes)
        logger.debug("process_list: %s", process_list)
        if not process_list:
            #No process running on ports
            logger.info("No running processes found")
            return False
        if "jsvc" in process_list:
            print "Tomcat (jsvc) process is running... "
            return True
        else:
            print " WARNING: There is another process running on expected Tomcat (jsvc) ports!!!! [%s] ?? " % (process_list)
            return False
    else:
        print " Warning Cannot find %s/conf/server.xml file!" % (config["tomcat_install_dir"])
        print " Using alternative method for checking on tomcat process..."
        ps_process = subprocess.Popen(shlex.split("ps -elf"), stdout=subprocess.PIPE)
        grep_process = subprocess.Popen(shlex.split("grep jsvc"), stdin=ps_process.stdout, stdout=subprocess.PIPE)
        grep_process_2 = subprocess.Popen(shlex.split("grep -v grep"), stdin=grep_process.stdout, stdout=subprocess.PIPE)
        awk_process = subprocess.Popen(shlex.split("awk ' END { print NR }'"), stdin=grep_process_2.stdout, stdout=subprocess.PIPE)

        ps_process.stdout.close()
        grep_process.stdout.close()
        grep_process_2.stdout.close()

        tomcat_process_stdout, tomcat_process_stderr = awk_process.communicate()
        logger.info("tomcat_process_stdout: %s", tomcat_process_stdout)
        logger.info("tomcat_process_stderr: %s", tomcat_process_stderr)

        # status_value = subprocess.Popen(shlex.split("ps -elf | grep jsvc | grep -v grep | awk ' END { print NR }'"))


def find_jars_in_directory(directory):
    ''' find the jar files in a given directory; return a string of colon delimited jar file names '''
    jar_string = ""
    files_in_directory = os.listdir(directory)
    for file in files_in_directory:
        if file.endswith(".jar"):
            if not jar_string:
                jar_string += file
            else:
                jar_string += (":"+file)
    return jar_string

def start_tomcat():
    status = check_tomcat_process()
    if status == 0:
        return 1
    elif status == 3:
        print "Please resolve this issue before starting tomcat!"
        esg_functions.exit_with_error(status)

    print "Starting Tomcat (jsvc)..."
    esg_bash2py.mkdir_p(config["tomcat_install_dir"]+"/work/Catalina", 0755)
    os.chown(config["tomcat_install_dir"]+"/work", pwd.getpwnam(config["tomcat_user"]).pw_uid, pwd.getpwnam(config["tomcat_user"]).pw_gid)
    os.chmod(config["tomcat_install_dir"]+"/work", 0755)

    current_directory = os.getcwd()
    os.chdir(config["tomcat_install_dir"])
    # copy_result = subprocess.check_output("$(find $(readlink -f `pwd`/bin/) | grep jar | xargs | perl -pe 's/ /:/g')", shell=True)
    tomcat_jars = find_jars_in_directory(config["tomcat_install_dir"])
    jsvc_launch_command=("JAVA_HOME=%s %s/bin/jsvc -Djava.awt.headless=true -Dcom.sun.enterprise.server.ss.ASQuickStartup=false"
        "-Dcatalina.home=%s -pidfile %s -cp %s -outfile %s/logs/catalina.out"
        "-errfile %s/logs/catalina.err "
        "-user %s %s %s -Dsun.security.ssl.allowUnsafeRenegotiation=false"
        "-Dtds.content.root.path=%s org.apache.catalina.startup.Bootstrap") % (config["java_install_dir"], config["tomcat_install_dir"], config["tomcat_install_dir"], config["tomcat_pid_file"], tomcat_jars, config["tomcat_install_dir"], config["tomcat_install_dir"], config["tomcat_user"], config["tomcat_opts"], config["java_opts"], config["thredds_content_dir"])
    if jsvc_launch_command != 0:
        print " ERROR: Could not start up tomcat"
        f = subprocess.Popen(['tail',"./logs/catalina.err"],\
                stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        # while True:
        #     line = f.stdout.readline()
        #     print line
        os.chdir(current_directory)
        esg_functions.exit_with_error(1)
    #Don't wait forever, but give tomcat some time before it starts
    # pcheck 10 2 1 -- check_tomcat_process
    # [ $? != 0 ] && echo "Tomcat couldn't be started."
    # sleep 2

def stop_tomcat():
    '''
        Stops Tomcat server from running. Does nothing if Tomcat is not currently running.
    '''
    if check_tomcat_process() !=0:
        return 1

    #TODO: modify to use pushd()
    current_directory = os.getcwd()
    os.chdir(config["tomcat_install_dir"])
    print "stop tomcat: %s/bin/jsvc -pidfile %s -stop org.apache.catalina.startup.Bootstrap" % (config["tomcat_install_dir"], config["tomcat_pid_file"])
    print "(please wait)"
    sleep(1)
    try:
        stop_tomcat_command = subprocess.Popen(shlex.split("{tomcat_install_dir}/bin/jsvc -pidfile {tomcat_pid_file} -stop org.apache.catalina.startup.Bootstrap".format(tomcat_install_dir=config["tomcat_install_dir"], tomcat_pid_file=config["tomcat_pid_file"])))
        stop_tomcat_stdout, stop_tomcat_stderr = stop_tomcat_command.communicate()
        logger.info("stop_tomcat_stdout: %s", stop_tomcat_stdout)
        logger.info("stop_tomcat_stderr: %s", stop_tomcat_stderr)
        if stop_tomcat_command.returncode != 0:
            kill_status = 0
            print " WARNING: Unable to stop tomcat, (nicely)"
            print " Hmmm...  okay no more mr nice guy... issuing "
            print  "\"pkill -9 $(cat ${tomcat_pid_file})\""
            kill_return_code = subprocess.check_output("kill -9 $(cat ${tomcat_pid_file}) >& /dev/null")
            kill_status += kill_return_code
            if kill_status != 0:
                print "Hmmm... still could not shutdown... process may have already been stopped"
    except OSError, error:
        logger.error("Could not stop Tomcat with jsvc script.")
        logger.error(error)
        return False
    # stop_tomcat_status = subprocess.check_output(config["tomcat_install_dir"]+"/bin/jsvc -pidfile"+ config["tomcat_pid_file"] +" -stop org.apache.catalina.startup.Bootstrap")
    subprocess.call("/bin/ps -elf | grep jsvc | grep -v grep")
    os.chdir(current_directory)
    return True

def build_jsvc():
    #----------
    #build jsvc (if necessary)
    #----------
    print "Checking for jsvc... "
    with esg_bash2py.pushd("bin"):
        logger.debug("Changed directory to %s", os.getcwd())
        # try:
        #     os.chdir("bin")
        #     logger.debug("Changed directory to %s", os.getcwd())
        # except OSError, error:
        #     logger.error(error)

        #https://issues.apache.org/jira/browse/DAEMON-246
        try:
            os.environ["LD_LIBRARY_PATH"]=os.environ["LD_LIBRARY_PATH"] + ":/lib" + config["word_size"]
        except KeyError, error:
            logger.error(error)

        if os.access(os.path.join("./", "jsvc"), os.X_OK):
            print "Found jsvc; no need to build"
            print "[OK]"
        else:
            print "jsvc Not Found"
            #TODO: Bash quirk where this would fail silently, must be changed as far as handling
            if not stop_tomcat():
                logger.error("Could not stop Tomcat before building jsvc")

            print "Building jsvc... (JAVA_HOME={java_install_dir})".format(java_install_dir = config["java_install_dir"])
            logger.debug("current directory: %s", os.getcwd())
            os.chdir("bin")
            logger.debug("current directory: %s", os.getcwd())
            if os.path.isfile("commons-daemon-native.tar.gz"):
                print "unpacking commons-daemon-native.tar.gz..."
                tar = tarfile.open("commons-daemon-native.tar.gz")
                tar.extractall()
                tar.close()
                try:
                    os.chdir("commons-daemon-1.0.15-native-src")
                    #It turns out they shipped with a conflicting .o file in there (oops) so I have to remove it manually.
                    logger.debug("Changed directory to %s", os.getcwd())
                    os.remove("./native/libservice.a")
                except OSError, error:
                    logger.error(error)
                subprocess.call(shlex.split("make clean"))
            elif os.path.isfile("jsvc.tar.gz "):
                print "unpacking jsvc.tar.gz..."
                tar = tarfile.open("jsvc.tar.gz")
                tar.extractall()
                tar.close()
                try:
                    os.chdir("jsvc-src")
                    logger.debug("Changed directory to %s", os.getcwd())
                except OSError, error:
                    logger.error(error)
                subprocess.call("autoconf")
            else:
                print "NOT ABLE TO INSTALL JSVC!"
                esg_functions.exit_with_error(1)

        _configure_tomcat_with_java()

def _configure_tomcat_with_java():
    logger.debug("current directory for configure_tomcat_with_java(): %s", os.getcwd())
    tomcat_configure_script_path = os.path.join(os.getcwd(), "unix", "configure")
    logger.info("tomcat_configure_script_path: %s", tomcat_configure_script_path)
    try:
        os.chmod(tomcat_configure_script_path, 0755)
    except OSError, error:
        logger.error(error)
        logger.error("Check if /usr/local/tomcat/configure script exists or if it is symlinked.")
        sys.exit(1)
    configure_string = "{configure} --with-java={java_install_dir}".format(configure = tomcat_configure_script_path, java_install_dir = config["java_install_dir"])
    subprocess.call(shlex.split(configure_string))
    subprocess.call(shlex.split(" make -j {number_of_cpus}".format(number_of_cpus = config["number_of_cpus"])))

def check_for_previous_tomcat_install(default_answer):
    if os.access(os.path.join(config["tomcat_install_dir"], "bin", "jsvc"), os.X_OK):
        print "Detected an existing tomcat installation..."
        if default_answer == "y":
            continue_installation_answer = raw_input( "Do you want to continue with Tomcat installation and setup? [Y/n]") or default_answer
        else:
            continue_installation_answer = raw_input( "Do you want to continue with Tomcat installation and setup? [y/N]") or default_answer

        if continue_installation_answer.lower() != "y" or not continue_installation_answer.lower() != "yes":
            print "Skipping tomcat installation and setup - will assume tomcat is setup properly"
            return True

def _check_for_tomcat_dist_dir(tomcat_parent_dir, tomcat_dist_dir, tomcat_dist_file):
    if not os.path.exists(os.path.join(tomcat_parent_dir, tomcat_dist_dir)):
        print "Don't see tomcat distribution dir {tomcat_parent_dir}/{tomcat_dist_dir}".format(tomcat_parent_dir = tomcat_parent_dir, tomcat_dist_dir =  tomcat_dist_dir)
        if not os.path.isfile(tomcat_dist_file):
            print "Don't see tomcat distribution file {pwd}/{tomcat_dist_file} either".format(pwd = os.getcwd(), tomcat_dist_file = tomcat_dist_file)
            print "Downloading Tomcat from {tomcat_dist_url}".format(tomcat_dist_url = config["tomcat_dist_url"])
            urllib.urlretrieve(config["tomcat_dist_url"], tomcat_dist_file)
            print "unpacking {tomcat_dist_file}...".format(tomcat_dist_file = tomcat_dist_file)
            tar = tarfile.open(tomcat_dist_file)
            tar.extractall(tomcat_parent_dir)
            tar.close()
    #If you don't see the directory but see the tar.gz distribution
    #then expand it
    if os.path.isfile(tomcat_dist_file) and not os.path.exists(os.path.join(tomcat_parent_dir, tomcat_dist_dir)):
        print "unpacking ${tomcat_dist_file}...".format(tomcat_dist_file = tomcat_dist_file)
        tar = tarfile.open(tomcat_dist_file)
        tar.extractall(tomcat_parent_dir)
        tar.close()

    if not os.path.exists(config["tomcat_install_dir"]):
        logger.info("Did not find existing Tomcat installation directory.  Creating %s ", config["tomcat_install_dir"])
        os.chdir(tomcat_parent_dir)
        try:
            os.symlink(tomcat_dist_dir, config["tomcat_install_dir"])
        except OSError, error:
            logger.error(" ERROR: Could not create sym link %s/%s -> %s", tomcat_parent_dir, tomcat_dist_dir, config["tomcat_install_dir"])
            logger.error(error)
        finally:
            os.chdir(config["workdir"])
    else:
        logger.info("Found previous Tomcat installation directory. Creating new symlink from %s/%s -> %s", tomcat_parent_dir, tomcat_dist_dir, config["tomcat_install_dir"])
        try:
            os.unlink(config["tomcat_install_dir"])
        except OSError, error:
            shutil.move(config["tomcat_install_dir"], config["tomcat_install_dir"] + "." + str(datetime.date.today())+".bak")
        finally:
            os.chdir(tomcat_parent_dir)
            try:
                os.symlink(tomcat_dist_dir, config["tomcat_install_dir"])
            except OSError, error:
                logger.error(" ERROR: Could not create sym link %s/%s -> %s", tomcat_parent_dir, tomcat_dist_dir, config["tomcat_install_dir"])
                logger.error(error)
            finally:
                os.chdir(config["workdir"])

def _create_tomcat_user():
    if not pwd.getpwnam(config["tomcat_user"]).pw_uid:
        logger.info(" WARNING: There is no tomcat user \"%s\" present on system", config["tomcat_user"])
        #NOTE: "useradd/groupadd" are a RedHat/CentOS thing... to make this cross distro compatible clean this up.
        try:
            tomcat_group_check = grp.getgrnam(
                config["tomcat_group"])
        except KeyError:
            groupadd_command = "/usr/sbin/groupadd -r %s" % (
                config["tomcat_group"])
            groupadd_output = subprocess.call(groupadd_command, shell=True)
            if groupadd_output != 0 or groupadd_output != 9:
                print "ERROR: *Could not add tomcat system group: %s" % (config["tomcat_group"])
                esg_functions.exit_with_error(1)

        useradd_command = '''/usr/sbin/useradd -r -c'Tomcat Server Identity' -g {tomcat_group} {tomcat_user} '''.format(tomcat_group = config["tomcat_group"], tomcat_user = config["tomcat_user"])
        useradd_output = subprocess.call(useradd_command, shell=True)
        if useradd_output != 0 or useradd_output != 9:
            print "ERROR: Could not add tomcat system account user {tomcat_user}".format(tomcat_user = config["tomcat_user"])
            esg_functions.exit_with_error(1)

def _upgrade_tomcat_version(existing_tomcat_directory):
    previous_tomcat_version = re.search("tomcat-(\S+)", esg_functions.readlinkf(existing_tomcat_directory)).group()
    new_tomcat_version = re.search("tomcat-(\S+)", esg_functions.readlinkf(config["tomcat_install_dir"])).group()
    print "Upgrading tomcat installation from {previous_tomcat_version} to {new_tomcat_version}".format(previous_tomcat_version = previous_tomcat_version, new_tomcat_version = new_tomcat_version)

    print "copying webapps... "
    src_files = os.listdir(os.path.join(existing_tomcat_directory, "webapps"))
    for file_name in src_files:
        full_file_name = os.path.join(existing_tomcat_directory, file_name)
        if os.path.isfile(full_file_name):
            shutil.copy(full_file_name, config["tomcat_install_dir"])

    print "copying configuration... "
    src_files = os.listdir(os.path.join(existing_tomcat_directory, "conf"))
    for file_name in src_files:
        full_file_name = os.path.join(existing_tomcat_directory, file_name)
        if os.path.isfile(full_file_name):
            shutil.copy(full_file_name, config["tomcat_install_dir"])

    print "copying logs... "
    src_files = os.listdir(os.path.join(existing_tomcat_directory, "logs"))
    for file_name in src_files:
        full_file_name = os.path.join(existing_tomcat_directory, file_name)
        if os.path.isfile(full_file_name):
            shutil.copy(full_file_name, config["tomcat_install_dir"])

    print "upgrade migration complete"

def _remove_unnecessary_webapps():
    os.chdir(os.path.join(config["tomcat_install_dir"], "webapps"))
    print "Checking for unnecessary webapps with dubious security implications as a precaution..."
    obsolete_directory_list =["examples", "docs",  "host-manager", "manager"]
    for directory in obsolete_directory_list:
        if not os.path.exists(directory):
            continue
        directory_full_path = esg_functions.readlinkf(directory)
        print "Removing {directory_full_path}".format(directory_full_path = directory_full_path)
        try:
            shutil.rmtree(directory_full_path)
            print "{directory_full_path} successfully deleted [OK]".format(directory_full_path = directory_full_path)
        except Exception, error:
            print "[FAIL]; Could not delete webapp"
            logger.error(error)

def setup_tomcat(devel = False, upgrade_flag = False, force_install = False):
    print "*******************************"
    print "Setting up Apache Tomcat...(v{tomcat_version})".format(tomcat_version = config["tomcat_version"])
    print "*******************************"

    existing_tomcat_directory = esg_functions.readlinkf(config["tomcat_install_dir"])

    if force_install:
        default = "y"
    else:
        default = "n"

    if check_for_previous_tomcat_install(default):
        return True

    esg_bash2py.mkdir_p(config["workdir"])

    starting_directory = os.getcwd()
    os.chdir(config["workdir"])

    tomcat_dist_file = esg_bash2py.trim_string_from_head(config["tomcat_dist_url"])
    tomcat_dist_dir = re.sub("\.tar.gz", "", tomcat_dist_file)

    #There is this pesky case of having a zero sized dist file...
    if os.path.exists(tomcat_dist_file):
        if os.stat(tomcat_dist_file).st_size == 0:
            os.remove(tomcat_dist_file)

    #Check to see if we have a tomcat distribution directory
    tomcat_parent_dir = re.search("^/\w+/\w+", config["tomcat_install_dir"]).group()

    _check_for_tomcat_dist_dir(tomcat_parent_dir, tomcat_dist_dir, tomcat_dist_file)

    #If there is no tomcat user on the system create one (double check that usradd does the right thing)
    _create_tomcat_user()

    try:
        os.chdir(config["tomcat_install_dir"])
        logger.debug("Changed directory to %s", os.getcwd())
    except OSError, error:
        logger.error(error)

    build_jsvc()

    if not os.path.isfile("/usr/lib/libcap.so") and os.path.isfile("/lib{word_size}/libcap.so".format(word_size = config["word_size"])):
        os.symlink("/lib{word_size}/libcap.so".format(word_size = config["word_size"]), "/usr/lib/libcap.so")

    os.chdir(config["tomcat_install_dir"])

    #----------------------------------
    # Upgrade logic...
    #----------------------------------
    if upgrade_flag:
        stop_tomcat()
        _upgrade_tomcat_version(existing_tomcat_directory)
    else:
        try:
            if os.stat(config['ks_secret_file']).st_size != 0:
                config["keystore_password"] = esg_functions.get_keystore_password()
                configure_tomcat(config["keystore_password"], esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist", devel=devel)
        except OSError, error:
            logger.error(error)
            logger.info("Attempting to get configure Tomcat with the security_admin_password")
            security_admin_password = esg_functions.get_security_admin_password()
            logger.debug("security_admin_password: %s", security_admin_password)
            configure_tomcat(security_admin_password, esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist", devel=devel)
    try:
        os.chown(esg_functions.readlinkf(config["tomcat_install_dir"]), pwd.getpwnam(config["tomcat_user"]).pw_uid, grp.getgrnam(
            config["tomcat_group"]).gr_gid)
    except Exception, error:
        print "**WARNING**: Could not change owner/group of {tomcat_install_dir} successfully".format(tomcat_install_dir = esg_functions.readlinkf(config["tomcat_install_dir"]))
        logger.error(error)

    #-------------------------------
    # Remove unnecessary webapps for Security Reasons...
    #-------------------------------
    _remove_unnecessary_webapps()

    os.chdir(config["tomcat_install_dir"])

    setup_root_app()

    esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"
    esg_functions.download_update(os.path.join(config["tomcat_install_dir"], "webapps","ROOT","robots.txt"), "{esg_dist_url}/robots.txt".format(esg_dist_url = esg_dist_url))
    esg_functions.download_update(os.path.join(config["tomcat_install_dir"], "webapps","ROOT","favicon.ico"), "{esg_dist_url}/favicon.ico".format(esg_dist_url = esg_dist_url))

    migrate_tomcat_credentials_to_esgf(esg_dist_url)
    sleep(1)
    start_tomcat()

    if tomcat_port_check():
        print "Tomcat ports checkout [OK]"
    else:
        logger.error("Tomcat Port Check failed")
        print "[FAIL]"
        esg_functions.exit_with_error(1)


    os.chdir(starting_directory)
    write_tomcat_env()
    write_tomcat_install_log()

    return True

def download_server_config_file(esg_dist_url):
    ''' Download the server.xml config file from the distribution mirror '''
    config_file_name = "server.xml"
    config_file_path = os.path.join(config["tomcat_install_dir"], "conf", config_file_name)

    if esg_functions.download_update(config_file_path, "{esg_dist_url}/externals/bootstrap/node.{config_file_name}-v{tomcat_version}".format(esg_dist_url = esg_dist_url, config_file_name = config_file_name, tomcat_version = esg_bash2py.trim_string_from_tail(config["tomcat_version"]))) != 0:
        esg_functions.exit_with_error(1)

    os.chmod(config_file_path, 0600)
    os.chown(config_file_path, pwd.getpwnam(config["tomcat_user"]).pw_uid, grp.getgrnam(config["tomcat_group"]).gr_gid)

def _set_keystore_password():
    while True:
        keystore_password_input = raw_input("Please enter the password for this keystore   : ")
        if keystore_password_input == "changeit":
                break
        if not keystore_password_input:
            print "Invalid password"
            continue

        keystore_password_input_confirmation = raw_input("Please re-enter the password for this keystore: ")
        if keystore_password_input == keystore_password_input_confirmation:
            config["keystore_password"] = keystore_password_input
            break
        else:
            print "Sorry, values did not match. Please try again."
            continue
    return True

def _get_esgf_host():
    ''' Get the esgf host name from the file; if not in file, return the fully qualified domain name (FQDN) '''
    try:
        esgf_host = config["esgf_host"]
    except KeyError:
        esgf_host = socket.getfqdn()

    return esgf_host

def _set_distinguished_name(esgf_host):
    #NOTE:
    #As Reference on Distingueshed Names (DNs)
    #http://download.oracle.com/javase/1.4.2/docs/tooldocs/windows/keytool.html
    #According to that document, case does not matter but ORDER DOES!
    #See script scope declaration of this variable (default_dname [suffix] = "OU=ESGF.ORG, O=ESGF")

    use_distinguished_name = "Y"
    try:
        distinguished_name
    except NameError:
        distinguished_name = config["default_distinguished_name"]

    distringuished_name_input = raw_input("Would you like to use the DN: [{distinguished_name}]?  [Y/n]".format(distinguished_name = distinguished_name))

    if distringuished_name_input.lower in ("n", "no", "y", "yes"):
        use_distinguished_name = distringuished_name_input

    if distringuished_name_input.lower() in ["yes", "y"]:
        distinguished_name = "CN={esgf_host}, {distinguished_name}".format(esgf_host = esgf_host, distinguished_name = distinguished_name)
        print "Using keystore DN = {distinguished_name}".format(distinguished_name = distinguished_name)

    logger.debug("Your selection is %s", use_distinguished_name)
    logger.debug("distinguished_name = %s", distinguished_name)

    return (distinguished_name, use_distinguished_name)

def extract_common_name(distinguished_name):
    common_name = re.search("(CN=)(\S+)(,)", distinguished_name).group(2)
    logger.info("regex on distinguished_name: %s", common_name)
    return common_name

def create_keystore(keystore_password):
    ''' Use the Java Keytool to create a keystore '''
    print "Launching Java's keytool:"

    if not len(config["keystore_password"]) > 0:
        _set_keystore_password()

    esgf_host = _get_esgf_host()
    distinguished_name, use_distinguished_name = _set_distinguished_name(esgf_host)

    if not distinguished_name or use_distinguished_name.lower() in ["n", "no"]:
        java_keytool_command = "{java_install_dir}/bin/keytool -genkey -alias {keystore_alias} -keyalg RSA \
        -keystore ${keystore_file} \
        -validity 365 -storepass {keystore_password}".format(java_install_dir = config["java_install_dir"],
            keystore_alias = config["keystore_alias"], keystore_file =config["keystore_file"], keystore_password = config["keystore_password"])

        java_keytool_process = esg_functions.call_subprocess(shlex.split(java_keytool_command))
        if java_keytool_process["returncode"] != 0:
            print " ERROR: keytool genkey command failed"
        esg_functions.exit_with_error(1)
    else:
        # distringuished_name_sed_output = subprocess.check_output("echo {distinguished_name} | sed -n 's#.*CN=\([^,]*\),.*#\1#p'".format(distinguished_name = distinguished_name))

        if extract_common_name(distinguished_name):

            java_keytool_command = '{java_install_dir}/bin/keytool -genkey -dname "{distinguished_name}" -alias \
            {keystore_alias} -keyalg RSA -keystore {keystore_file} -validity 365 \
            -storepass {store_password} -keypass {store_password}'.format(java_install_dir = config["java_install_dir"],
            keystore_alias = config["keystore_alias"], keystore_file = config["keystore_file"], keystore_password = keystore_password, distinguished_name=distinguished_name)

            java_keytool_process = esg_functions.call_subprocess(shlex.split(java_keytool_command))
            if java_keytool_process["returncode"] != 0:
                print " ERROR: keytool genkey command failed"
            esg_functions.exit_with_error(1)

def _download_truststore_file():
    #Fetch/Copy truststore to $tomcat_conf_dir
    #(first try getting it from distribution server otherwise copy Java's)
    if not os.path.isfile(config["truststore_file"]):
        # i.e. esg-truststore.ts
        truststore_file_name = esg_bash2py.trim_string_from_tail(config["truststore_file"])
        if esg_functions.download_update(truststore_file_name, "http://{esg_dist_url_root}/certs/{truststore_file_name}".format(esg_dist_url_root = config["esg_dist_url_root"], truststore_file_name = truststore_file_name)) > 1:
            print " INFO: Could not download certificates {truststore_file_name} for tomcat - will copy local java certificate file".format(truststore_file_name = truststore_file_name)
            #NOTE: The truststore uses the java default password: "changeit"
            try:
                shutil.copyfile(os.path.join(config["java_install_dir"], "jre", "lib", "security", "cacerts"), config["truststore_file"])
                logger.info("Copied default Java truststore")
                print "(note - the truststore password will probably not match! The password for the default Java truststore is 'changeit')"
            except Exception, error:
                print " ERROR: Could not fetch or copy {truststore_file_name} for tomcat!!".format(truststore_file_name = truststore_file_name)
                logger.error(error)

def configure_tomcat(keystore_password, esg_dist_url, devel=False):
    #----------------------------
    # TOMCAT Configuration...
    #----------------------------

    print "*******************************"
    print "Configuring Tomcat... (for Node Manager)"
    print "*******************************"
    with esg_bash2py.pushd(os.path.join(config["tomcat_install_dir"], "conf")):
        logger.info("Changed directory to: %s", os.getcwd())

        download_server_config_file(esg_dist_url)

        print "Looking for keystore [{keystore_file}]...".format(keystore_file = config["keystore_file"])
        if os.path.isfile(config["keystore_file"]):
            print "Found keystore file"
            print "Using existing keystore \"{keystore_file}\"".format(keystore_file =config["keystore_file"])
        else:
            print "Could not find keystore file"
            #Create a keystore in $tomcat_conf_dir
            print "Keystore setup: "
            create_keystore(keystore_password)

        setup_temp_ca(devel)
        _download_truststore_file()

        #Edit the server.xml file to contain proper location of certificates
        logger.debug("Editing %s/conf/server.xml accordingly...", config["tomcat_install_dir"])
        edit_tomcat_server_xml(config["keystore_password"])

        add_my_cert_to_truststore("--keystore-pass",config["keystore_password"])

        try:
            os.chown(esg_functions.readlinkf(config["tomcat_install_dir"]), pwd.getpwnam(config["tomcat_user"]).pw_uid, grp.getgrnam(
                config["tomcat_group"]).gr_gid)
        except Exception, error:
            print "**WARNING**: Could not change owner/group of {tomcat_install_dir} successfully".format(tomcat_install_dir = esg_functions.readlinkf(config["tomcat_install_dir"]))
            logger.error(error)
            esg_functions.exit_with_error(1)

        try:
            os.chown(esg_functions.readlinkf(config["tomcat_conf_dir"]), pwd.getpwnam(config["tomcat_user"]).pw_uid, grp.getgrnam(
                config["tomcat_group"]).gr_gid)
        except Exception, error:
            print "**WARNING**: Could not change owner/group of {tomcat_conf_dir} successfully".format(tomcat_conf_dir = esg_functions.readlinkf(config["tomcat_conf_dir"]))
            logger.error(error)
            esg_functions.exit_with_error(1)

def edit_tomcat_server_xml(keystore_password):
    server_xml_path = os.path.join(config["tomcat_install_dir"],"conf", "server.xml")
    tree = etree.parse(server_xml_path)
    root = tree.getroot()

    pathname = root.find(".//Resource[@pathname]")
    pathname.set('pathname', config["tomcat_users_file"])
    connector_element = root.find(".//Connector[@truststoreFile]")
    connector_element.set('truststoreFile', config["truststore_file"])
    connector_element.set('truststorePass', config["truststore_password"])
    connector_element.set('keystoreFile', config["keystore_file"])
    connector_element.set('keystorePass', keystore_password)
    connector_element.set('keyAlias', config["keystore_alias"])
    tree.write(open(server_xml_path, "wb"), pretty_print = True)
    tree.write(os.path.join(config["tomcat_install_dir"],"conf", "test_output.xml"), pretty_print = True)

def java_keytool_list(java_install_dir, keystore_file, keystore_password):
    ''' Runs the list option of the Java Keytool '''
    keytool_list_command = "{java_install_dir}/bin/keytool -v -list -keystore {local_keystore_file} \
    -storepass {local_keystore_password}".format(java_install_dir = config["java_install_dir"],
    local_keystore_file = keystore_file.strip(), local_keystore_password = keystore_password)
    logger.debug("keytool_list_command: %s", keytool_list_command)

    keytool_list_process = esg_functions.call_subprocess(keytool_list_command)

    return keytool_list_process


def add_my_cert_to_truststore(action, value):
    '''
        This takes our certificate from the keystore and adds it to the
        truststore.  This is done for other services that use originating
        from this server talking to another service on this same host.  This
        is the interaction scenario with part of the ORP security mechanism.
        The param here is the password of the *keystore*  <----Stale comment; doesn't match functionality
    '''
    _glean_keystore_info()

    #TODO: refactor to better name
    local_keystore_file = config["keystore_file"]
    local_keystore_password = config["keystore_password"]
    local_keystore_alias = config["keystore_alias"]
    local_truststore_file = config["truststore_file"]
    local_truststore_password = config["truststore_password"]
    check_private_keystore_flag = True

    if action in ["--keystore", "-ks"]:
        local_keystore_file = value
        logger.debug("keystore_file: %s", local_keystore_file)
    elif action in ["--keystore-pass", "-kpass"]:
        local_keystore_password = value
        logger.debug("keystore_pass_value: %s", local_keystore_password)
    elif action in ["alias", "-a"]:
        local_keystore_password = value
        logger.debug("key_alias_value: %s", local_keystore_password)
    elif action in ["--truststore", "-ts"]:
        local_truststore_file = value
        logger.debug("truststore_file_value: %s", local_truststore_file)
    elif action in ["--truststore-pass", "-tpass"]:
        local_truststore_file = value
        logger.debug("truststore_pass_value: %s", local_truststore_file)
    elif action in ["--no-check"]:
        check_private_keystore_flag = False
    else:
        logger.error("Invalid action given: %s", action)
        return False

    logger.debug("keystore_file: %s", local_keystore_file)
    logger.debug("keystore_pass_value: %s", local_keystore_password)
    logger.debug("key_alias_value: %s", local_keystore_alias)
    logger.debug("truststore_file_value: %s", local_truststore_file)
    logger.debug("truststore_pass_value: %s", local_truststore_password)
    logger.debug("check_private_keystore_flag: %s", check_private_keystore_flag)

    keystore_password_in_file = esg_functions.get_keystore_password()

    if keystore_password_in_file != local_keystore_file:
        if _set_keystore_password():
            local_keystore_password = esg_functions.get_keystore_password()

            keytool_list_process = java_keytool_list(config["java_install_dir"], local_keystore_file, local_keystore_password)

            if keytool_list_process["returncode"] != 0:
                print "([FAIL]) Could not access private keystore {local_keystore_file} with provided password. Try again...".format(local_keystore_file = local_keystore_file)


    if check_private_keystore_flag:
        #only making this call to test password
        keytool_list_process = java_keytool_list(config["java_install_dir"], local_keystore_file, local_keystore_password)

        if keytool_list_process["returncode"] != 0:
            print "([FAIL]) Could not access private keystore {local_keystore_file} with provided password. (re-run --add-my-cert-to-truststore)".format(local_keystore_file = local_keystore_file)
            return False
        else:
            logger.info("[OK]")

        logger.debug("Peforming checks against configured values...")

        keystore_password_md5 = esg_functions.get_md5sum_password(config["keystore_password"])
        local_keystore_password_md5 = esg_functions.get_md5sum_password(local_keystore_password)

        logger.debug(keystore_password_md5 == local_keystore_password_md5)

        if config["keystore_password"] != local_keystore_password:
            logger.info("\nWARNING: password entered does not match what's in the app server's configuration file\n")

            # Update server.xml
            server_xml_object = etree.parse(os.path.join(config["tomcat_install_dir"], "conf", "server.xml"))
            root = server_xml_object.getroot()
            connector_element = root.find(".//Connector[@truststoreFile]")
            connector_element.set('keystorePass', local_keystore_password)

            print "  Adjusted app server's config file... "
            config["keystore_password"] = connector_element.get('keystorePass')

            if config["keystore_password"] != local_keystore_password:
                logger.info("[OK]")
            else:
                logger.error("[FAIL]")

    #----------------------------------------------------------------
    #Re-integrate my public key (I mean, my "certificate") from my keystore into the truststore (the place housing all public keys I allow to talk to me)
    #----------------------------------------------------------------
    if os.path.exists(local_truststore_file):
        print "Re-Integrating keystore's certificate into truststore.... "
        print "Extracting keystore's certificate... "
        java_keytool_command = "{java_install_dir}/bin/keytool -export -alias {local_keystore_alias}  -file {local_keystore_file}.cer -keystore {local_keystore_file} \
-storepass {local_keystore_password}".format(java_install_dir = config["java_install_dir"],
        local_keystore_file = local_keystore_file, local_keystore_password = local_keystore_password, local_keystore_alias =  local_keystore_alias)
        logger.debug("java_keytool_command: %s", java_keytool_command)
        keytool_return_code = subprocess.call(shlex.split(java_keytool_command))
        if keytool_return_code == 0:
            logger.info("[OK]")
        else:
            logger.error("[FAIL]")
            sys.exit(1)

    java_keytool_command = "{java_install_dir}/bin/keytool -v -list -keystore {local_truststore_file} \
        -storepass {local_truststore_password}".format(java_install_dir = config["java_install_dir"],
        local_truststore_file = local_truststore_file, local_truststore_password = local_truststore_password)
    grep_for_alias_commmand = "egrep -i '^Alias[ ]+name:[ ]+'{local_keystore_alias}'$'".format(local_keystore_alias = local_keystore_alias)
    keytool_subprocess = subprocess.Popen(shlex.split(java_keytool_command), stdout = subprocess.PIPE)
    grep_for_alias_subprocess = subprocess.Popen(shlex.split(grep_for_alias_commmand), stdin = keytool_subprocess.stdout, stdout = subprocess.PIPE)

    # Allow proc1 to receive a SIGPIPE if proc2 exits.
    keytool_subprocess.stdout.close()
    stdout_processes, stderr_processes = grep_for_alias_subprocess.communicate()
    logger.info("stdout_processes: %s", stdout_processes)
    logger.info("stderr_processes: %s", stderr_processes)
    logger.info("grep_for_alias_subprocess.returncode: %s", grep_for_alias_subprocess.returncode)

    if grep_for_alias_subprocess.returncode == 0:
        print "Detected Alias \"{local_keystore_alias}\" Present... Removing... Making space for certificate... ".format(local_keystore_alias = local_keystore_alias)

        delete_keytool_alias_command = "{java_install_dir}/bin/keytool -delete -alias {local_keystore_alias} -keystore {local_truststore_file} \
        -storepass {local_truststore_password}".format(java_install_dir = config["java_install_dir"],
        local_truststore_file = local_truststore_file, local_truststore_password = local_truststore_password, local_keystore_alias =  local_keystore_alias)
        logger.debug("delete_keytool_alias_command: %s", delete_keytool_alias_command)

        delete_keytool_alias_return_code = subprocess.call(shlex.split(delete_keytool_alias_command))
        if delete_keytool_alias_return_code != 1:
            logger.error(" ERROR: problem deleting %s key from keystore!", local_keystore_alias)
            return False

    print "Importing keystore's certificate into truststore... "
    import_keystore_cert_command = "{java_install_dir}/bin/keytool -import -v -trustcacerts -alias {local_keystore_alias} -keypass {local_keystore_password} -file {local_keystore_file}.cer -keystore {local_truststore_file} \
        -storepass {local_truststore_password} -noprompt".format(java_install_dir = config["java_install_dir"], local_keystore_alias = local_keystore_alias,
        local_keystore_password = local_keystore_password, local_keystore_file = local_keystore_file,
        local_truststore_file = local_truststore_file, local_truststore_password = local_truststore_password)
    import_keystore_cert_return_code = subprocess.call(shlex.split(import_keystore_cert_command))
    if import_keystore_cert_return_code == 0:
        logger.info("[OK]")
    else:
        logger.error("[FAIL]")
        sys.exit(1)
    sync_with_java_truststore(local_truststore_file)
    print "cleaning up after ourselves... "
    try:
        os.remove(local_keystore_file+".cer")
    except Exception, error:
        logger.error("[FAIL]: %s", error)

    os.chown(local_truststore_file, pwd.getpwnam(config["tomcat_user"]).pw_uid, grp.getgrnam(
            config["tomcat_group"]).gr_gid)

    return True


def sync_with_java_truststore(external_truststore = config["truststore_file"]):
    if not os.path.exists(os.path.join(os.environ["JAVA_HOME"], "jre", "lib", "security", "jssecacerts")) and os.path.exists(os.path.join(os.environ["JAVA_HOME"], "jre", "lib", "security", "cacerts")):
        shutil.copyfile(os.path.join(os.environ["JAVA_HOME"], "jre", "lib", "security", "cacerts"), os.path.join(os.environ["JAVA_HOME"], "jre", "lib", "security", "jssecacerts"))

    java_truststore = os.path.join(os.environ["JAVA_HOME"], "jre", "lib", "security", "jssecacerts")
    print "Syncing {external_truststore} with {java_truststore} ... ".format(external_truststore = external_truststore, java_truststore = java_truststore)
    if not os.path.exists(external_truststore):
        logger.error("[FAIL]: Cannot locate %s", external_truststore)
        return False

    if filecmp.cmp(external_truststore, java_truststore):
        logger.info("Files are equivalent: [OK]")
        return True
    if os.path.exists(java_truststore):
        shutil.copyfile(java_truststore, java_truststore+".bak")
    shutil.copyfile(external_truststore, java_truststore)
    os.chmod(java_truststore, 0644)
    os.chown(java_truststore, config["installer_uid"], config["installer_gid"])


def _glean_keystore_info():
    '''
        Util "private" function for use **AFTER** tomcat has been configured!!!!
        Reads tomcat's server.xml file at sets the appropriate vars based on contained values
        Will *only* set global vars if it was successfully gleaned from server.xml.
    '''
    if os.access(os.path.join(config["tomcat_install_dir"], "conf", "server.xml"), os.R_OK):
        logger.debug("inspecting tomcat config file ")

        server_xml_object = etree.parse(os.path.join(config["tomcat_install_dir"], "conf", "server.xml"))
        root = server_xml_object.getroot()
        connector_element = root.find(".//Connector[@truststoreFile]")

        logger.info("keystoreFile: %s", connector_element.get('keystoreFile'))
        config["keystore_file"] = connector_element.get('keystoreFile')
        logger.debug("keystore_file_value: %s", config["keystore_file"])

        config["keystore_password"] = connector_element.get('keystorePass')
        logger.debug("keystore_pass_value: %s", config["keystore_password"])

        logger.debug("connector_element.get('keyAlias'): %s", connector_element.get('keyAlias'))
        config["keystore_alias"] = connector_element.get('keyAlias')
        logger.debug("key_alias_value: %s", config["keystore_alias"])

        config["truststore_file"] = connector_element.get('truststoreFile')
        logger.debug("truststore_file_value: %s", config["truststore_file"])

        config["truststore_password"] = connector_element.get('truststorePass')
        logger.debug("truststore_pass_value: %s", config["truststore_password"])

        return True
    else:
        print "Could not glean values store... :-("
        return False

def delete_existing_temp_ca_files():
    try:
        shutil.rmtree(os.path.join(os.getcwd(), "CA"))
    except OSError, error:
        logger.error(error)

    extensions_to_delete = (".pem", ".gz", ".ans", ".tmpl")
    files = os.listdir(os.getcwd())
    for file_name in files:
        if file_name.endswith(extensions_to_delete):
            try:
                os.remove(os.path.join(os.getcwd(), file_name))
                logger.debug("removed %s", os.path.join(os.getcwd(), file_name))
            except OSError, error:
                logger.error(error)

def download_temp_ca_scripts(devel):
    if devel:
        urllib.urlretrieve("http://{esg_coffee_dist_url_root}/devel/esgf-installer/CA.pl".format(esg_coffee_dist_url_root = config["esg_coffee_dist_url_root"]), "CA.pl")
        urllib.urlretrieve("http://{esg_coffee_dist_url_root}/devel/esgf-installer/openssl.cnf".format(esg_coffee_dist_url_root = config["esg_coffee_dist_url_root"]), "openssl.cnf")
        urllib.urlretrieve("http://{esg_coffee_dist_url_root}/devel/esgf-installer/myproxy-server.config".format(esg_coffee_dist_url_root = config["esg_coffee_dist_url_root"]), "myproxy-server.config")
    else:
        urllib.urlretrieve("http://{esg_coffee_dist_url_root}/esgf-installer/CA.pl".format(esg_coffee_dist_url_root = config["esg_coffee_dist_url_root"]), "CA.pl")
        urllib.urlretrieve("http://{esg_coffee_dist_url_root}/esgf-installer/openssl.cnf".format(esg_coffee_dist_url_root = config["esg_coffee_dist_url_root"]), "openssl.cnf")
        urllib.urlretrieve("http://{esg_coffee_dist_url_root}/esgf-installer/myproxy-server.config".format(esg_coffee_dist_url_root = config["esg_coffee_dist_url_root"]), "myproxy-server.config")

def create_setupca_ans_file(host_name):
    setupca_ans_tmpl = open("setupca.ans.tmpl", "r")
    setupca_ans = open("setupca.ans", "w+")
    for line in setupca_ans_tmpl:
        setupca_ans.write(line.replace("placeholder.fqdn", host_name))
    setupca_ans_tmpl.close()
    setupca_ans.close()

def create_reqhost_ans_file(host_name):
    reqhost_ans_tmpl = open("reqhost.ans.tmpl", "r")
    reqhost_ans = open("reqhost.ans", "w+")
    for line in reqhost_ans_tmpl:
        reqhost_ans.write(line.replace("placeholder.fqdn", host_name))
    reqhost_ans_tmpl.close()
    reqhost_ans.close()


def generate_new_ca():
    ''' Create a new CA using the CA.pl perl script: Creates the CA directory and populates it
        From CA.pl script comment:
        CA -newca ... will setup the right stuff;
    '''

    print "\n*******************************"
    print "Generate New CA"
    print "******************************* \n"

    new_ca_process = subprocess.Popen(shlex.split("perl CA.pl -newca"))
    new_ca_process.communicate()

def generate_rsa_key():
    ''' Creates a new RSA key from the CA/private/cakey.pem and writes it out as clearkey.pem '''

    print "\n*******************************"
    print "Generate New RSA Key"
    print "******************************* \n"

    generate_rsa_key_process = subprocess.Popen(shlex.split("openssl rsa -in CA/private/cakey.pem -out clearkey.pem -passin pass:placeholderpass"))
    generate_rsa_key_process.communicate()
    if generate_rsa_key_process.returncode == 0:
        logger.debug("moving clearkey")
        shutil.move("clearkey.pem", "/etc/tempcerts/CA/private/cakey.pem")

def generate_request_cert():
    #-newreq: creates a new certificate request. The private key and request are written to the file newreq.pem

    print "\n*******************************"
    print "Generate New Certificate Request"
    print "******************************* \n"

    with open("reqhost.ans", "rb") as reqhost_ans_file:
        reqhost_ans = reqhost_ans_file.read().strip()
        logger.info("reqhost_ans: %s", reqhost_ans)

        request_cert_process = subprocess.Popen(shlex.split("perl CA.pl -newreq-nodes"))
        # request_cert_process.stdin.write(reqhost_ans)
        request_cert_process.communicate()
        # esg_functions.call_subprocess("perl CA.pl -newreq-nodes", command_stdin = reqhost_ans_file.read().strip())

def sign_certificate():
    ''' Sign a generate certificate using the CA.pl perl script
        # CA -sign ... will sign the generated request and output
    '''

    print "\n*******************************"
    print "Sign Certificate"
    print "******************************* \n"

    sign_certificate_process = subprocess.Popen(shlex.split("perl CA.pl -sign"))
    sign_certificate_process.communicate()
    # with open("setuphost.ans", "rb") as setuphost_ans_file:
    #     esg_functions.call_subprocess("perl CA.pl -sign ", command_stdin = setuphost_ans_file.read().strip())

def write_to_ca_cert_pem():
    ''' The x509 command is a multi purpose certificate utility. It can be used to display certificate information,
        convert certificates to various forms, sign certificate
        requests like a "mini CA" or edit certificate trust settings. '''

    print "\n*******************************"
    print "Write to cacert.pem"
    print "******************************* \n"

    with open("cacert.pem", "wb") as cacert_file:
        output_process = subprocess.Popen(shlex.split("openssl x509 -in CA/cacert.pem -inform pem -outform pem"), stdout=subprocess.PIPE)
        output_stdout, output_stderr = output_process.communicate()
        print output_stdout
        cacert_file.write(output_stdout)

def write_to_host_cert():
    print "\n*******************************"
    print "Write to hostcert.pem"
    print "******************************* \n"

    with open("hostcert.pem", "w") as hostcert_file:
        #inform = input format; set to pem.  outform = output format; set to pem
        hostcert_ssl_process = esg_functions.call_subprocess("openssl x509 -in newcert.pem -inform pem -outform pem")
        hostcert_file.write(hostcert_ssl_process["stdout"])
        logger.info("hostcert_ssl_process: %s", hostcert_ssl_process)
    shutil.move("newkey.pem", "hostkey.pem")

def delete_new_temp_cert():
    for file_name in glob.glob("new*.pem"):
        logger.debug("file_name: %s", file_name)
        try:
            os.remove(file_name)
            logger.debug("deleted: %s", file_name)
        except OSError, error:
            logger.error(error)

def get_cert_subject(cert):
    cert_info = crypto.load_certificate(crypto.FILETYPE_PEM, open(esg_functions.readlinkf(cert)).read())
    cert_subject = cert_info.get_subject()
    cert_subject = re.sub(" <X509Name object '|'>", "", str(cert_subject)).strip()
    logger.info("cert_subject: %s", cert_subject)
    return cert_subject

def setup_temp_ca(devel):
    try:
        esgf_host = config["esgf_host"]
    except KeyError:
        esgf_host = esg_property_manager.get_property("esgf_host")

    host_name = esgf_host

    esg_bash2py.mkdir_p("/etc/tempcerts")

    os.chdir("/etc/tempcerts")
    logger.debug("Changed directory to %s", os.getcwd())

    delete_existing_temp_ca_files()

    os.mkdir("CA")
    write_ca_ans_templ()
    write_reqhost_ans_templ()

    setuphost_ans = open("setuphost.ans", "w+")
    setuphost_ans.write("y\ny")
    setuphost_ans.close()

    create_setupca_ans_file(host_name)
    create_reqhost_ans_file(host_name)

    download_temp_ca_scripts(devel)

    generate_new_ca()
    generate_rsa_key()
    generate_request_cert()
    sign_certificate()
    write_to_ca_cert_pem()

    shutil.copyfile("CA/private/cakey.pem", "cakey.pem")
    write_to_host_cert()

    try:
        os.chmod("cakey.pem", 0400)
        os.chmod("hostkey.pem", 0400)
    except OSError, error:
        logger.error(error)

    delete_new_temp_cert()

    ESGF_OPENSSL = "/usr/bin/openssl"
    cert = "cacert.pem"
    temp_subject = '/O=ESGF/OU=ESGF.ORG/CN=placeholder'
    # quoted_temp_subject = subprocess.check_output("`echo {temp_subject} | sed 's/[./*?|]/\\\\&/g'`;".format(temp_subject = temp_subject))
    cert_subject = get_cert_subject(cert)

    # quoted_cert_subject = subprocess.check_output("`echo {cert_subject} | sed 's/[./*?|]/\\\\&/g'`;".format(cert_subject = cert_subject))
    # print "quotedcertsubj=~{quoted_cert_subject}~".format(quoted_cert_subject = quoted_cert_subject)

    local_hash = subprocess.Popen(shlex.split("{ESGF_OPENSSL} x509 -in {cert} -noout -hash".format(ESGF_OPENSSL =  ESGF_OPENSSL, cert = cert)), stdout = subprocess.PIPE)
    local_hash_output, local_hash_err = local_hash.communicate()
    local_hash_output = local_hash_output.strip()
    logger.debug("local_hash_output: %s", local_hash_output)
    logger.debug("local_hash_err: %s", local_hash_err)

    target_directory = "globus_simple_ca_{local_hash}_setup-0".format(local_hash = local_hash_output)

    esg_bash2py.mkdir_p(target_directory)

    shutil.copyfile(cert, os.path.join(target_directory, "{local_hash}.0".format(local_hash = local_hash_output)))

    print_templ()

    #Find and replace the temp_subject with the cert_subject in the signing_policy_template and rewrite to new file.

    # subprocess.call(shlex.split('sed "s/\(.*\)$quotedtmpsubj\(.*\)/\1$quotedcertsubj\2/" signing_policy_template >$tgtdir/${localhash}.signing_policy;'))

    signing_policy_template = open("signing_policy_template", "r")
    signing_policy = open("signing_policy", "w+")
    for line in signing_policy_template:
        signing_policy.write(line.replace(temp_subject, cert_subject))
    signing_policy_template.close()
    signing_policy.close()

    # shutil.copyfile(os.path.join(target_directory,local_hash_output,".signing_policy"), "signing_policy")

    subprocess.call(shlex.split("tar -cvzf globus_simple_ca_{local_hash}_setup-0.tar.gz {target_directory}".format(local_hash = local_hash_output, target_directory = target_directory)))
    subprocess.call(shlex.split("rm -rf {target_directory};".format(target_directory = target_directory)))
    subprocess.call(shlex.split("rm -f signing_policy_template;"))

    esg_bash2py.mkdir_p("/etc/certs")

    try:
        shutil.copy("openssl.cnf", os.path.join("/etc", "certs"))

        for file in glob.glob("host*.pem"):
            shutil.copy(file, os.path.join("/etc", "certs"))

        shutil.copyfile("cacert.pem", os.path.join("/etc", "certs", "cachain.pem"))
    except IOError, error:
        logger.error(error)

    esg_bash2py.mkdir_p("/etc/esgfcerts")

def extract_root_app(root_app_name):
    print '''\n
    *******************************
    unpacking {root_app_name}...
    *******************************'''.format(root_app_name=root_app_name)
    try:
        tar = tarfile.open(root_app_name)
        tar.extractall()
        tar.close()
        shutil.move("ROOT", os.path.join(config["tomcat_install_dir"], "webapps"))
    except Exception, error:
        logger.error(error)
        print "ERROR: Could not extract {root_app_name}".format(root_app_name=esg_functions.readlinkf(root_app_name))

def copy_index_html_files():
    print '''\n
    *******************************
    Copying index.html to node manager and web frontend directories
    ******************************* '''
    if os.path.exists(os.path.join(config["tomcat_install_dir"], "webapps", "esgf-node-manager")):
        shutil.copyfile(os.path.join(config["tomcat_install_dir"], "webapps", "ROOT","index.html"), os.path.join(config["tomcat_install_dir"], "webapps", "ROOT","index.html.nm"))
    if os.path.exists(os.path.join(config["tomcat_install_dir"], "webapps", "esgf-web-fe")):
        shutil.copyfile(os.path.join(config["tomcat_install_dir"], "webapps", "ROOT","index.html"), os.path.join(config["tomcat_install_dir"], "webapps", "ROOT","index.html.fe"))

def setup_root_app():
    try:
        if os.path.isdir(os.path.join(config["tomcat_install_dir"], "webapps", "ROOT")) and 'REFRESH' in open(os.path.join(config["tomcat_install_dir"], "webapps", "ROOT","index.html")).read():
            print "ROOT app in place... [OK]"
            return True
        else:
            raise IOError
    except IOError, error:
        logger.error(error)
        print "Oops, Don't see ESGF ROOT web application"
        esg_functions.backup(os.path.join(config["tomcat_install_dir"], "webapps", "ROOT"))

        print "\n*******************************"
        print "Setting up Apache Tomcat...(v{tomcat_version}) ROOT webapp".format(tomcat_version = config["tomcat_version"])
        print "******************************* \n"

        esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"
        root_app_dist_url = "{esg_dist_url}/ROOT.tgz".format(esg_dist_url = esg_dist_url)

        esg_bash2py.mkdir_p(config["workdir"])

        starting_directory = os.getcwd()
        os.chdir(config["workdir"])

        print "\nDownloading ROOT application from {root_app_dist_url}".format(root_app_dist_url = root_app_dist_url)
        if esg_functions.download_update(root_app_dist_url) > 0:
            print "ERROR: Could not download ROOT app archive"
            esg_functions.exit_with_error(1)

        root_app_name = esg_bash2py.trim_string_from_head(root_app_dist_url)
        extract_root_app(root_app_name)

        copy_index_html_files()

        os.chown(esg_functions.readlinkf(os.path.join(config["tomcat_install_dir"], "webapps", "ROOT")), pwd.getpwnam(config["tomcat_user"]).pw_uid, grp.getgrnam(
            config["tomcat_group"]).gr_gid)

        print "ROOT application \"installed\""
        os.chdir(starting_directory)
        return True

def write_ca_ans_templ():
    file = open("setupca.ans.tmpl", "w+")
    file.write('''

        placeholder.fqdn-CA


        ''')
    file.close()

def write_reqhost_ans_templ():
    file = open("reqhost.ans.tmpl", "w+")
    file.write('''

        placeholder.fqdn


        ''')
    file.close()

def print_templ():
    file = open("signing_policy_template", "w+")
    file.write('''
        # ca-signing-policy.conf, see ca-signing-policy.doc for more information
        #
        # This is the configuration file describing the policy for what CAs are
        # allowed to sign whoses certificates.
        #
        # This file is parsed from start to finish with a given CA and subject
        # name.
        # subject names may include the following wildcard characters:
        #    *    Matches any number of characters.
        #    ?    Matches any single character.
        #
        # CA names must be specified (no wildcards). Names containing whitespaces
        # must be included in single quotes, e.g. 'Certification Authority'.
        # Names must not contain new line symbols.
        # The value of condition attribute is represented as a set of regular
        # expressions. Each regular expression must be included in double quotes.
        #
        # This policy file dictates the following policy:
        #   -The Globus CA can sign Globus certificates
        #
        # Format:
        #------------------------------------------------------------------------
        #  token type  | def.authority |                value
        #--------------|---------------|-----------------------------------------
        # EACL entry #1|

         access_id_CA      X509         '/O=ESGF/OU=ESGF.ORG/CN=placeholder'

         pos_rights        globus        CA:sign

         cond_subjects     globus       '"/O=ESGF/OU=ESGF.ORG/*"'

        # end of EACL

        ''')
    file.close()


def migrate_tomcat_credentials_to_esgf(esg_dist_url):
    '''
    Move selected config files into esgf tomcat's config dir (certificate et al)
    Ex: /esg/config/tomcat
    -rw-r--r-- 1 tomcat tomcat 181779 Apr 22 19:44 esg-truststore.ts
    -r-------- 1 tomcat tomcat    887 Apr 22 19:32 hostkey.pem
    -rw-r--r-- 1 tomcat tomcat   1276 Apr 22 19:32 keystore-tomcat
    -rw-r--r-- 1 tomcat tomcat    590 Apr 22 19:32 pcmdi11.llnl.gov-esg-node.csr
    -rw-r--r-- 1 tomcat tomcat    733 Apr 22 19:32 pcmdi11.llnl.gov-esg-node.pem
    -rw-r--r-- 1 tomcat tomcat    295 Apr 22 19:42 tomcat-users.xml

    Only called when migration conditions are present.
    '''
    tomcat_install_conf = os.path.join(config["tomcat_install_dir"], "conf")

    if tomcat_install_conf != config["tomcat_conf_dir"]:
        if not os.path.exists(config["tomcat_conf_dir"]):
            esg_bash2py.mkdir_p(config["tomcat_conf_dir"])

        esg_functions.backup(tomcat_install_conf)

        logger.debug("Moving credential files into node's tomcat configuration dir: %s", config["tomcat_conf_dir"])
        truststore_file_name = esg_bash2py.trim_string_from_head(config["truststore_file"])
        # i.e. /usr/local/tomcat/conf/esg-truststore.ts
        if os.path.exists(os.path.join(tomcat_install_conf, truststore_file_name)) and not os.path.exists(config["truststore_file"]):
            shutil.move(os.path.join(tomcat_install_conf, truststore_file_name), config["truststore_file"])
            print "+"

        keystore_file_name = esg_bash2py.trim_string_from_head(config["keystore_file"])
        if os.path.exists(os.path.join(tomcat_install_conf, keystore_file_name)) and not os.path.exists(config["keystore_file"]):
            shutil.move(os.path.join(tomcat_install_conf, keystore_file_name), config["keystore_file"])
            print "+"

        tomcat_users_file_name = esg_bash2py.trim_string_from_head(config["tomcat_users_file"])
        if os.path.exists(os.path.join(tomcat_install_conf, tomcat_users_file_name)) and not os.path.exists(config["tomcat_users_file"]):
            shutil.move(os.path.join(tomcat_install_conf, tomcat_users_file_name), config["tomcat_users_file"])
            print "+"

        if os.path.exists(os.path.join(tomcat_install_conf, "hostkey.pem")) and not os.path.exists(os.path.join(config["tomcat_conf_dir"], "hostkey.pem")):
            shutil.move(os.path.join(tomcat_install_conf, "hostkey.pem"), os.path.join(config["tomcat_conf_dir"], "hostkey.pem"))
            print "+"

        try:
            if os.path.exists(os.path.join(tomcat_install_conf, config["esgf_host"] +"-esg-node.csr")) and not os.path.exists(os.path.join(config["tomcat_conf_dir"], config["esgf_host"] +"-esg-node.csr")):
                shutil.move(os.path.join(tomcat_install_conf, config["esgf_host"] +"-esg-node.csr"), os.path.join(config["tomcat_conf_dir"], config["esgf_host"] +"-esg-node.csr"))

            if os.path.exists(os.path.join(tomcat_install_conf, config["esgf_host"] +"-esg-node.pem")) and not os.path.exists(os.path.join(config["tomcat_conf_dir"], config["esgf_host"] +"-esg-node.pem")):
                shutil.move(os.path.join(tomcat_install_conf, config["esgf_host"] +"-esg-node.pem"), os.path.join(config["tomcat_conf_dir"], config["esgf_host"] +"-esg-node.pem"))
        except KeyError:
            if os.path.exists(os.path.join(tomcat_install_conf, socket.getfqdn() +"-esg-node.csr")) and not os.path.exists(os.path.join(config["tomcat_conf_dir"], socket.getfqdn() +"-esg-node.csr")):
                shutil.move(os.path.join(tomcat_install_conf, socket.getfqdn() +"-esg-node.csr"), os.path.join(config["tomcat_conf_dir"], socket.getfqdn() +"-esg-node.csr"))

            if os.path.exists(os.path.join(tomcat_install_conf, socket.getfqdn() +"-esg-node.pem")) and not os.path.exists(os.path.join(config["tomcat_conf_dir"], socket.getfqdn() +"-esg-node.pem")):
                shutil.move(os.path.join(tomcat_install_conf, socket.getfqdn() +"-esg-node.pem"), os.path.join(config["tomcat_conf_dir"], socket.getfqdn() +"-esg-node.pem"))

        os.chown(config["tomcat_conf_dir"], pwd.getpwnam(config["tomcat_user"]).pw_uid, grp.getgrnam(config["tomcat_group"]).gr_gid)

        #Be sure that the server.xml file contains the explicit Realm specification needed.
        server_xml_path = os.path.join(config["tomcat_install_dir"],"conf", "server.xml")
        tree = etree.parse(server_xml_path)
        root = tree.getroot()
        realm_element = root.find(".//Realm")
        if realm_element is None:
            download_server_config_file(esg_dist_url)

        #SET the server.xml variables to contain proper values
        logger.debug("Editing %s/conf/server.xml accordingly...", config["tomcat_install_dir"])
        edit_tomcat_server_xml(config["keystore_password"])

def set_esgf_http_port(root):
    print '''\n
    *******************************
    Set ESGF HTTP Port
    *******************************'''
    http_port_element = root.find(".//Connector[@protocol='HTTP/1.1']")
    esgf_http_port = http_port_element.get("port")
    logger.debug("esgf_http_port: %s", esgf_http_port)
    return esgf_http_port

def set_esgf_https_port(root):
    print '''\n
    *******************************
    Set ESGF HTTPS Port
    *******************************'''
    esgf_https_port_element = root.find(".//Connector[@SSLEnabled]")
    esgf_https_port = esgf_https_port_element.get("port")
    logger.debug("esgf_https_port: %s", esgf_https_port)
    return esgf_https_port

def tomcat_port_check():
    '''
        Helper function to poke at tomcat ports...
        Port testing for http and https
    '''
    return_all = True
    failed_connections = 0
    protocol = "http"
    print "\nChecking connection at all ports described in {tomcat_install_dir}/conf/server.xml".format(tomcat_install_dir =  config["tomcat_install_dir"])
    server_xml_path = os.path.join(config["tomcat_install_dir"],"conf", "server.xml")
    ports = find_tomcat_ports(server_xml_path)
    for port in ports:
        if port == "8223":
            continue
        if port == "8443":
            protocol="https"
        print "checking localhost port [{port}]".format(port = port)
        tcp_socket = socket.socket()
        try:
            tcp_socket.connect(("localhost", int(port)))
            print "Connected to %s on port %s" % ("localhost", port)
            # return True
        except socket.error, error:
            print "Connection to %s on port %s failed: %s" % ("localhost", port, error)
            failed_connections +=1
            logger.debug("failed_connections after increment: %s", failed_connections)

    tree = etree.parse(server_xml_path)
    root = tree.getroot()

    esgf_http_port = set_esgf_http_port(root)
    esgf_https_port = set_esgf_https_port(root)

    #We only care about reporting a failure for ports below 1024
    #specifically 80 (http) and 443 (https)
    logger.debug("failed_connections: %s", failed_connections)
    if failed_connections > 0:
        return False
    return True


def write_tomcat_env():
    pass

def write_tomcat_install_log():
    pass

# test_tomcat() {
#
#     echo
#     echo "----------------------------"
#     echo "Tomcat Test...  "
#     echo "----------------------------"
#     echo
#     start_tomcat
#     tomcat_port_check && echo "Tomcat ports checkout $([OK])" || ([FAIL] && popd && checked_done 1)
#     checked_done 0
# }
