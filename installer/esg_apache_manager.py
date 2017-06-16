import os
import subprocess
import shutil
import datetime
import logging
import socket
import shlex
import filecmp
import git
import esg_bash2py
import esg_version_manager
import esg_functions
from esg_init import EsgInit


logging.basicConfig(format = "%(levelname): %(lineno)s %(funcName)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

config = EsgInit()

def clone_apache_repo(devel):
    try:
        git.Repo.clone_from(config.config_dictionary["apache_frontend_repo"], "apache_frontend")
    except git.exc.GitCommandError, error:
        logger.error(error)
        logger.error("Git repo already exists.")

    if os.path.isdir(os.path.join("apache_frontend", ".git")):
        logger.error("Successfully cloned repo from %s", config.config_dictionary["apache_frontend_repo"])
        # os.chdir("apache-frontend")
        # logger.debug("changed directory to %s:", os.getcwd())
        apache_frontend_repo_local = git.Repo("/usr/local/src/esgf/workbench/esg/apache_frontend/apache_frontend")
        if devel == 1:
            apache_frontend_repo_local.git.checkout("devel")
        else:
            apache_frontend_repo_local.git.checkout("master")

def stop_httpd():
    stop_httpd_process = esg_functions.call_subprocess("/etc/init.d/httpd stop")
    if stop_httpd_process["returncode"] != 0:
        logger.error("Could not stop the httpd process")

def start_httpd():
    #TODO: investigate why this uses a different binary than stop_httpd()
    start_httpd_process = esg_functions.call_subprocess(shlex.split("/etc/init.d/esgf-httpd start"))
    if start_httpd_process["returncode"] != 0:
        logger.error("Could not start the httpd process")


def setup_apache_frontend(devel = False):
    print '''
    *******************************
    Setting up Apache Frontend
    ******************************* \n'''

    old_directory = os.getcwd()
    try:
        local_work_directory = os.environ["ESGF_INSTALL_WORKDIR"]
    except KeyError, error:
        logger.debug(error)
        local_work_directory = os.path.join(config.config_dictionary["installer_home"], "workbench", "esg")

    os.chdir(local_work_directory)
    logger.debug("changed directory to %s:", os.getcwd())
    esg_bash2py.mkdir_p("apache_frontend")
    os.chdir("apache_frontend")
    logger.debug("changed directory to %s:", os.getcwd())

    print "Fetching the Apache Frontend Repo from GIT Repo... %s" % (config.config_dictionary["apache_frontend_repo"])
    clone_apache_repo(devel)

    try:
        host_name = esgf_host
    except NameError, error:
        logger.error(error)
        host_name = socket.gethostname()

        stop_httpd()
        
        check_config_command = "chkconfig --levels 2345 httpd off"
        check_config_process = subprocess.Popen(shlex.split(check_config_command))
        check_config_process_stdout, check_config_process_stderr =  check_config_process.communicate()

        ip_addresses = []

        while True:
            ip_address = raw_input("Enter a single ip address which would be cleared to access admin restricted pages.\nYou will be prompted if you want to enter more ip-addresses: ")
            ip_addresses.append(ip_address)

            add_more_ips = raw_input("Do you wish to allow more ip addresses to access admin restricted pages? y/n:")
            if add_more_ips.lower() != "y":
                break

        allowed_ip_address_string = "".join("Allow from " + address + "\t" for address in ip_addresses)
        logger.debug("allowed_ip_address_string: %s", allowed_ip_address_string)

        #Replace permitted-ips placeholder with permitted ips-values
        with open("/etc/httpd/conf/esgf-httpd.conf", "r") as esgf_httpd_conf_file:
            filedata = esgf_httpd_conf_file.read()
            filedata.replace("#insert-permitted-ips-here", "#permitted-ips-start-here\n" +allowed_ip_address_string +"\t#permitted-ips-end-here")

        with open("/etc/httpd/conf/esgf-httpd.conf", "w") as file:
                file.write(filedata)


        # add_ips_to_conf_file_command = "sed -i 's/\#insert-permitted-ips-here/\#permitted-ips-start-here\n{allowed_ip_address_string}\t\#permitted-ips-end-here/' /etc/httpd/conf/esgf-httpd.conf".format(allowed_ip_address_string = allowed_ip_address_string)
        # add_ips_to_conf_file_process = subprocess.Popen(shlex.split(add_ips_to_conf_file_command))
        # add_ips_to_conf_file_stdout, add_ips_to_conf_file_stderr = add_ips_to_conf_file_process.communicate()
        # logger.debug("add_ips_to_conf_file_stdout: %s", add_ips_to_conf_file_stdout)
        # logger.debug("add_ips_to_conf_file_stderr: %s", add_ips_to_conf_file_stderr)

        #Write the contents of /etc/tempcerts/cacert.pem  to /etc/certs/esgf-ca-bundle.crt
        esgf_ca_bundle_file = open("/etc/certs/esgf-ca-bundle.crt", "a")
        with open ("/etc/tempcerts/cacert.pem", "r") as cacert_file:
            cacert_contents = cacert_file.read()
            esgf_ca_bundle_file.write(cacert_contents)
        esgf_ca_bundle_file.close()

        start_httpd()
    else:
        config_file = "/etc/httpd/conf/esgf-httpd.conf"
        if os.path.isfile(config_file):
            esgf_httpd_version_command = "`grep ESGF-HTTPD-CONF $conf_file | awk '{print $4}'`"
            esgf_httpd_version_process = subprocess.Popen(shlex.split(esgf_httpd_version_command))
            esgf_httpd_version_stdout, esgf_httpd_version_stderr = esgf_httpd_version_process.communicate()
            if not esgf_httpd_version_stdout:
                logger.error("esgf-httpd.conf is missing versioning, attempting to update.")
                update_apache_conf(devel)
            else:
                if esg_version_manager.check_version_atleast(esgf_httpd_version_stdout, config.config_dictionary["apache_frontend_version"]) == 0:
                    logger.info("esgf-httpd.conf version is sufficient")
                else:
                    logger.info("esgf-httpd version is out-of-date, attempting to update.")
                    update_apache_conf(devel)
        else:
            logger.info("esgf-httpd.conf file not found, attempting to update. This condition is not expected to occur and should be reported to ESGF support")
            update_apache_conf()



def update_apache_conf(devel = False):
    try:
        local_work_directory = os.environ["ESGF_INSTALL_WORKDIR"]
    except KeyError, error:
        logger.debug(error)
        local_work_directory = os.path.join(config.config_dictionary["installer_home"], "workbench", "esg")

    config_file = "/etc/httpd/conf/esgf-httpd.conf"

    with esg_bash2py.pushd(local_work_directory):
        logger.debug("changed to directory: %s", os.getcwd())
        if not os.path.isdir("apache_frontend"):
            esg_bash2py.mkdir_p("apache_frontend")
            with esg_bash2py.pushd("apache_frontend"):
                logger.debug("changed to directory: %s", os.getcwd())
                git.Repo.clone_from(config.config_dictionary["apache_frontend_repo"], "apache_frontend")
            logger.debug("changed to directory: %s", os.getcwd())
        else:
            with esg_bash2py.pushd("apache_frontend"):
                logger.debug("changed to directory: %s", os.getcwd())
                shutil.rmtree("apache-frontend")
                git.Repo.clone_from(config.config_dictionary["apache_frontend_repo"], "apache_frontend")
            logger.debug("changed to directory: %s", os.getcwd())
        with esg_bash2py.pushd("apache_frontend/apache-frontend"):
            logger.debug("changed to directory: %s", os.getcwd())
            apache_frontend_repo_local = git.Repo("apache-frontend")
            if devel == 1:
                apache_frontend_repo_local.git.checkout("devel")
            else:
                apache_frontend_repo_local.git.checkout("master")

            if os.path.isfile(config_file):
                logger.info("Backing up previous version of %s", config_file)
                date_string = str(datetime.date.today())
                config_file_backup_name = config_file+date_string+".bak"
                if os.path.isfile(config_file_backup_name):
                    logger.info("WARNING:  esgf-httpd.conf already backed up today.")
                    shutil.copyfile(config_file_backup_name, config_file_backup_name+".1")
                else:
                    shutil.copyfile(config_file, config_file_backup_name)

            wsgi_path = "/opt/esgf/python/lib/python2.7/site-packages/mod_wsgi/server/mod_wsgi-py27.so"
            allowed_ips_sed_process = subprocess.Popen(shlex.split("sed -n '/\#permitted-ips-start-here/,/\#permitted-ips-end-here/p' /etc/httpd/conf/esgf-httpd.conf"), stdout=subprocess.PIPE)
            allowed_ips_grep_process = subprocess.Popen(shlex.split("grep Allow"), stdin = allowed_ips_sed_process.stdout, stdout=subprocess.PIPE)
            allowed_ips_sort_process = subprocess.Popen(shlex.split("sort -u"), stdin = allowed_ips_grep_process)

            allowed_ips_sed_process.stdout.close()
            allowed_ips_grep_process.stdout.close()
            allowed_ips_stdout, allowed_ips_stderr = allowed_ips_sort_process.communicate()
            logger.debug("allowed_ips_stdout: %s", allowed_ips_stdout)
            logger.debug("allowed_ips_stderr: %s", allowed_ips_stderr)

            permitted_ips_command = 'sed "s/\#permitted-ips-end-here/\#permitted-ips-end-here\n\t\#insert-permitted-ips-here/" /etc/httpd/conf/esgf-httpd.conf >etc/httpd/conf/esgf-httpd.conf;'
            permitted_ips_process = subprocess.Popen(shlex.split(permitted_ips_command))
            permitted_ips_stdout, permitted_ips_stderr = permitted_ips_process.communicate()
            logger.debug("permitted_ips_stdout: %s", permitted_ips_stdout)
            logger.debug("permitted_ips_stderr: %s", permitted_ips_stderr)
            with open("etc/httpd/conf/esgf-httpd.conf", "a") as httpd_conf_file:
                httpd_conf_file.write(permitted_ips_stdout)

            wsgi_path_module_sed_command = 'sed -i "s/\(.*\)LoadModule wsgi_module {wsgi_path}\(.*\)/\1LoadModule wsgi_module placeholder_so\2/" etc/httpd/conf/esgf-httpd.conf;'.format(wsgi_path = wsgi_path)
            wsgi_path_module_sed_process = subprocess.Popen(shlex.split(wsgi_path_module_sed_command))
            wsgi_path_module_sed_stdout, wsgi_path_module_sed_stderr = wsgi_path_module_sed_process.communicate()
            logger.debug("wsgi_path_module_sed_stdout: %s", wsgi_path_module_sed_stdout)
            logger.debug("wsgi_path_module_sed_stderr: %s", wsgi_path_module_sed_stderr)

            #TODO: Terrible names; figure out what they are representing and rename 
            include_httpd_locals_file = "Include /etc/httpd/conf/esgf-httpd-locals.conf"
            include_httpd_local_file = "Include /etc/httpd/conf/esgf-httpd-local.conf"

            #TODO: Another terrible name
            uncommented_include_httpd_locals_file = False
            uncommented_include_httpd_local_file = False

            #TODO: for now, adding full path to avoid confusion with the two etc directories
            with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "r") as file:
                filedata = file.read()
                if not "#Include /etc/httpd/conf/esgf-httpd-locals.conf" in filedata:
                    uncommented_include_httpd_locals_file = True
                    filedata = filedata.replace("Include /etc/httpd/conf/esgf-httpd-locals.conf", "#Include /etc/httpd/conf/esgf-httpd-locals.conf")
                if not '#Include /etc/httpd/conf/esgf-httpd-local.conf' in filedata:
                    uncommented_include_httpd_local_file = True 
                    filedata = filedata.replace("Include /etc/httpd/conf/esgf-httpd-local.conf", "#Include /etc/httpd/conf/esgf-httpd-local.conf")
            
            with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "w") as file:
                file.write(filedata)

            #Write first 22 lines? to different file
            original_server_lines_file = open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/original_server_lines", "w")
            with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "r") as esgf_httpd_conf_file:
                for i in range(22):
                    original_server_lines_file.write(esgf_httpd_conf_file.readline())

            original_server_lines_file.close()

            default_server_lines_file = open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/default_server_lines", "w")
            with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/tc/httpd/conf/esgf-httpd.conf.tmpl", "r") as esgf_httpd_conf_template:
                for i in range(22):
                    default_server_lines_file.write(esgf_httpd_conf_template.readline())


            #delete lines 1 through 22 from the files
            with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "r") as esgf_httpd_conf_file:
                lines = esgf_httpd_conf_file.readlines()
            lines = lines[22:]
            with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "w") as esgf_httpd_conf_file:
                esgf_httpd_conf_file.write(lines)

            with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf.tmpl", "r") as esgf_httpd_conf_template:
                lines = esgf_httpd_conf_file.readlines()
            lines = lines[22:]
            esgf_httpd_conf_template.write(lines)

            #check if esgf-httpd.conf and esgf-httpd.conf.tmpl are equivalent, i.e. take the diff
            if filecmp.cmp("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf.tmpl"):
                #we have changes; add allowed ips, ext file selection and wsgi path to latest template and apply
                logger.info("Detected changes. Will update and reapply customizations. An esg-node restart would be needed to read in the changes.")

                #write /etc/httpd/conf/esgf-httpd.conf.tmpl into /etc/httpd/conf/origsrvlines
                original_server_lines_file = open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/original_server_lines", "a")
                with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf.tmpl") as esgf_httpd_conf_template:
                    content = esgf_httpd_conf_template.read()
                original_server_lines_file.write(content)
                original_server_lines_file.close()

                shutil.move("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/original_server_lines", "/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf.tmpl")
                shutil.copyfile("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf.tmpl", "/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf")

                replace_wsgi_module_placeholder_command = 'sed -i "s/\(.*\)LoadModule wsgi_module placeholder_so\(.*\)/\1LoadModule wsgi_module {wsgi_path}\2/" etc/httpd/conf/esgf-httpd.conf;'.format(wsgi_path = wsgi_path)
                replace_wsgi_module_placeholder_process = subprocess.Popen(shlex.split(replace_wsgi_module_placeholder_command))
                replace_wsgi_module_placeholder_stdout, replace_wsgi_module_placeholder_stderr = replace_wsgi_module_placeholder_process.communicate()

                insert_permitted_ips_command = 'sed -i "s/\#insert-permitted-ips-here/\#permitted-ips-start-here\n{allowed_ips}\n\t#permitted-ips-end-here/" etc/httpd/conf/esgf-httpd.conf;'.format(allowed_ips = allowed_ips_stdout)
                insert_permitted_ips_process = subprocess.Popen(shlex.split(insert_permitted_ips_command))
                insert_permitted_ips_stdout, insert_permitted_ips_stderr = insert_permitted_ips_process.communicate()

                if uncommented_include_httpd_locals_file or uncommented_include_httpd_local_file:
                    with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "r") as file:
                        filedata = file.read()
                        filedata = filedata.replace("#Include /etc/httpd/conf/esgf-httpd-locals.conf", "Include /etc/httpd/conf/esgf-httpd-locals.conf") 
                        filedata = filedata.replace("#Include /etc/httpd/conf/esgf-httpd-local.conf", "Include /etc/httpd/conf/esgf-httpd-local.conf")
                    
                    with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "w") as file:
                        file.write(filedata)

                shutil.copyfile("/etc/httpd/conf/esgf-httpd.conf", "/etc/httpd/conf/esgf-httpd.conf.bak")
                shutil.copyfile("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "/etc/httpd/conf/esgf-httpd.conf")
            else:
                logger.info("No changes detected in apache frontend conf.")