'''Module for installing Apache and mod_wsgi. Also contains Apache process management functions'''
import os
import shutil
import logging
import datetime
import ConfigParser
from distutils.spawn import find_executable
import yaml
from esgf_utilities import esg_property_manager
from esgf_utilities import pybash
from esgf_utilities import esg_functions
from plumbum.commands import ProcessExecutionError

logger = logging.getLogger("esgf_logger" + "." + __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


def check_for_apache_installation():
    '''Check for existing httpd installation'''
    return find_executable("httpd")

def start_apache():
    '''Start httpd server'''
    esg_functions.call_binary("service", ["httpd", "start"])


def stop_apache():
    '''Stop httpd server'''
    esg_functions.call_binary("service", ["httpd", "stop"])


def restart_apache():
    '''Restart httpd server'''
    esg_functions.call_binary("service", ["httpd", "restart"])


def check_apache_status():
    '''Check httpd status'''
    try:
        esg_functions.call_binary("service", ["httpd", "status"])
    except ProcessExecutionError as error:
        # Return code of 3 indicates process is not running
        if error.retcode == 3:
            return False
        raise
    return True


def run_apache_config_test():
    '''Run httpd config test'''
    esg_functions.call_binary("service", ["httpd", "configtest"])


def check_apache_version():
    esg_functions.call_binary("httpd", ["-version"])


def install_apache_httpd():
    '''Install apache from yum'''
    pkg_list = ["mod_ssl"]
    
    if check_for_apache_installation():
        print "Found existing Apache installation."
        check_apache_version()

        try:
            setup_apache_answer = esg_property_manager.get_property(
                "update.apache")
        except ConfigParser.NoOptionError:
            setup_apache_answer = raw_input(
                "Would you like to continue the Apache installation anyway? [y/N]: ") or "N"

        if setup_apache_answer.lower() not in ["no", "n"]:
            pkg_list += ["httpd", "httpd-devel"]
    else:
        pkg_list += ["httpd", "httpd-devel"]

    esg_functions.call_binary("yum", ["-y", "install"] + pkg_list)


def install_mod_wsgi():
    '''Have to ensure python is install properly with the shared library for mod_wsgi installation to work'''
    print "\n*******************************"
    print "Setting mod_wsgi"
    print "******************************* \n"

    esg_functions.pip_install("mod_wsgi==4.5.3")
    esg_functions.call_binary("mod_wsgi-express", ["install-module"])

def make_python_eggs_dir():
    '''Create Python egg directories'''
    pybash.mkdir_p("/var/www/.python-eggs")
    apache_user_id = esg_functions.get_user_id("apache")
    apache_group_id = esg_functions.get_group_id("apache")
    os.chown("/var/www/.python-eggs", apache_user_id, apache_group_id)


def copy_apache_conf_files():
    ''' Copy custom apache conf files '''
    pybash.mkdir_p("/etc/certs")
    remote_bundle = "{}/certs/{}".format(
        esg_property_manager.get_property("esg.root.url"),
        "esgf-ca-bundle.crt"
    )
    esg_functions.download_update("/etc/certs/esgf-ca-bundle.crt", remote_bundle)
    # Custom ESGF Apache files that setup proxying
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "apache_conf/esgf-httpd"), "/etc/init.d/esgf-httpd")
    os.chmod("/etc/init.d/esgf-httpd", 0755)
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "apache_conf/esgf-httpd.conf"), "/etc/httpd/conf/esgf-httpd.conf")
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "apache_conf/esgf-httpd-local.conf"), "/etc/httpd/conf/esgf-httpd-local.conf")
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "apache_conf/esgf-httpd-locals.conf"), "/etc/httpd/conf/esgf-httpd-locals.conf")
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "apache_html/index.html"), "/var/www/html/index.html")
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "apache_conf/ssl.conf"), "/etc/httpd/conf.d/ssl.conf")
    shutil.copyfile("/etc/sysconfig/httpd", "/etc/sysconfig/httpd-{}".format(datetime.date.today()))

    # append tempcert to cert_bundle
    try:
        with open("/etc/certs/esgf-ca-bundle.crt", "a") as cert_bundle_file:
            cert_bundle_file.write(open("/etc/tempcerts/cacert.pem").read())
    except OSError:
        logger.exception()

    # add LD_LIBRARY_PATH to /etc/sysconfig/httpd
    with open("/etc/sysconfig/httpd", "a") as httpd_file:
        httpd_file.write("OPTIONS='-f /etc/httpd/conf/esgf-httpd.conf'\n")
        httpd_file.write("export LD_LIBRARY_PATH=/usr/local/conda/envs/esgf-pub/lib/:/usr/local/conda/envs/esgf-pub/lib/python2.7/:/usr/local/conda/envs/esgf-pub/lib/python2.7/site-packages/mod_wsgi/server\n")

def main():
    print "\n*******************************"
    print "Setting up Apache (httpd) Web Server"
    print "******************************* \n"

    install_apache_httpd()
    stop_apache()
    esg_functions.call_binary("chkconfig", ["--levels", "2345", "httpd", "off"])
    install_mod_wsgi()
    make_python_eggs_dir()
    copy_apache_conf_files()


if __name__ == '__main__':
    main()
