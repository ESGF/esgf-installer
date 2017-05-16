'''
Tomcat Management Functions
'''
import os
import subprocess
import pwd
import re
import logging
import shlex
from time import sleep
from esg_init import EsgInit
import esg_bash2py
import esg_functions


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
config = EsgInit()

def check_tomcat_process():
    '''
        Checks for the status of the Tomcat process
    '''
    server_xml_path = os.path.join(config.config_dictionary["tomcat_install_dir"], "conf", "server.xml")
    logger.debug("server_xml_path: %s", server_xml_path)
    if os.path.isfile(server_xml_path):
        try:
            esgf_host_ip
        except NameError:
             esgf_host_ip = get_property("esgf_host_ip")
        ports = []
        with open(server_xml_path, "r") as server_xml_file:
            for line in server_xml_file:
                line = line.rstrip() # remove trailing whitespace such as '\n'
                port_descriptor = re.search('(port=)(\S+)', line)
                if port_descriptor != None:
                    port_number = port_descriptor.group(2)
                    ports.append(port_number.replace('"', ''))

        logger.debug("ports: %s", ports)
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
            return 1
        if "jsvc" in process_list:
            print "Tomcat (jsvc) process is running... " 
            return 0
        else:
            print " WARNING: There is another process running on expected Tomcat (jsvc) ports!!!! [%s] ?? " % (process_list)
            return 3
    else:
        print " Warning Cannot find %s/conf/server.xml file!" % (config.config_dictionary["tomcat_install_dir"])
        print " Using alternative method for checking on tomcat process..."
        status_value = subprocess.Popen(shlex.split("ps -elf | grep jsvc | grep -v grep | awk ' END { print NR }'"))

def start_tomcat():
    pass
    status = check_tomcat_process()
    if status == 0:
        return 1
    elif status == 3:
        print "Please resolve this issue before starting tomcat!"
        checked_done(status)

    print "Starting Tomcat (jsvc)..."

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
    '''
        Stops Tomcat server from running. Does nothing if Tomcat is not currently running.
    '''
    if check_tomcat_process() !=0:
        return 1

    #TODO: modify to use pushd()
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


