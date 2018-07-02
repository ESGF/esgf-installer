'''Module for installing Apache and mod_wsgi. Also contains Apache process management functions'''
import os
import shutil
import logging
import datetime
import ConfigParser
from distutils.spawn import find_executable
import yaml
import pip
from esgf_utilities import esg_property_manager
from esgf_utilities import pybash
from esgf_utilities import esg_functions

logger = logging.getLogger("esgf_logger" + "." + __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


def check_for_apache_installation():
    if find_executable("httpd"):
        return True
    else:
        return False


def start_apache():
    return esg_functions.call_subprocess("service httpd start")


def stop_apache():
    esg_functions.stream_subprocess_output("service httpd stop")


def restart_apache():
    esg_functions.stream_subprocess_output("service httpd restart")


def check_apache_status():
    return esg_functions.call_subprocess("service httpd status")


def run_apache_config_test():
    esg_functions.stream_subprocess_output("service httpd configtest")


def install_apache_httpd():
    esg_functions.stream_subprocess_output("yum -y update")
    esg_functions.stream_subprocess_output(
        "yum install -y httpd httpd-devel mod_ssl")
    esg_functions.stream_subprocess_output("yum clean all")

    # Custom ESGF Apache files that setup proxying
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "apache_conf/esgf-httpd"), "/etc/init.d/esgf-httpd")
    os.chmod("/etc/init.d/esgf-httpd", 0755)
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "apache_conf/esgf-httpd.conf"),
                    "/etc/httpd/conf/esgf-httpd.conf")
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "apache_conf/esgf-httpd-local.conf"),
                    "/etc/httpd/conf/esgf-httpd-local.conf")
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "apache_conf/esgf-httpd-locals.conf"),
                    "/etc/httpd/conf/esgf-httpd-locals.conf")


def install_mod_wsgi():
    '''Have to ensure python is install properly with the shared library for mod_wsgi installation to work'''
    print "\n*******************************"
    print "Setting mod_wsgi"
    print "******************************* \n"

    try:
        pip._internal.main(['install', "mod_wsgi==4.5.3"])
    except AttributeError:
        pip.main(['install', "mod_wsgi==4.5.3"])
    with pybash.pushd("/etc/httpd/modules"):
        # If installer running in a conda env
        if "conda" in find_executable("python"):
            pybash.symlink_force(
                "/usr/local/conda/envs/esgf-pub/lib/python2.7/site-packages/mod_wsgi/server/mod_wsgi-py27.so", "/etc/httpd/modules/mod_wsgi-py27.so")
        else:
            pybash.symlink_force(
                "/usr/local/lib/python2.7/site-packages/mod_wsgi/server/mod_wsgi-py27.so", "/etc/httpd/modules/mod_wsgi-py27.so")

def make_python_eggs_dir():
    pybash.mkdir_p("/var/www/.python-eggs")
    apache_user_id = esg_functions.get_user_id("apache")
    apache_group_id = esg_functions.get_group_id("apache")
    os.chown("/var/www/.python-eggs", apache_user_id, apache_group_id)


def copy_apache_conf_files():
    ''' Copy custom apache conf files '''
    pybash.mkdir_p("/etc/certs")
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "apache_certs/esgf-ca-bundle.crt"),
                    "/etc/certs/esgf-ca-bundle.crt")
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "apache_html/index.html"), "/var/www/html/index.html")
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "apache_conf/ssl.conf"), "/etc/httpd/conf.d/ssl.conf")
    shutil.copyfile("/etc/sysconfig/httpd", "/etc/sysconfig/httpd-{}".format(datetime.date.today()))

    #add LD_LIBRARY_PATH to /etc/sysconfig/httpd
    with open("/etc/sysconfig/httpd", "a") as httpd_file:
        httpd_file.write("OPTIONS='-f /etc/httpd/conf/esgf-httpd.conf'\n")
        httpd_file.write("export LD_LIBRARY_PATH=/usr/local/conda/envs/esgf-pub/lib/:/usr/local/conda/envs/esgf-pub/lib/python2.7/:/usr/local/conda/envs/esgf-pub/lib/python2.7/site-packages/mod_wsgi/server\n")

    #append tempcert to cert_bundle
    try:
        with open("/etc/certs/esgf-ca-bundle.crt", "a") as cert_bundle_file:
            cert_bundle_file.write(open("/etc/tempcerts/cacert.pem").read())
    except OSError:
        logger.exception()

# def copy_files():
#     shutil.copyfile("/etc/sysconfig/httpd", "/etc/sysconfig/httpd-{}".format(datetime.date.today()))
#
#     #add LD_LIBRARY_PATH to /etc/sysconfig/httpd
#     with open("/etc/sysconfig/httpd", "a") as httpd_file:
#         httpd_file.write(open(os.path.join(os.path.dirname(__file__), "apache_conf/ldval.tmpl")).read())



def main():
    print "\n*******************************"
    print "Setting up Apache (httpd) Web Server"
    print "******************************* \n"

    if check_for_apache_installation():
        print "Found existing Apache installation."
        esg_functions.call_subprocess("httpd -version")

        try:
            setup_apache_answer = esg_property_manager.get_property(
                "update.apache")
        except ConfigParser.NoOptionError:
            setup_apache_answer = raw_input(
                "Would you like to continue the Apache installation anyway? [y/N]: ") or "N"

        if setup_apache_answer.lower() in ["no", "n"]:
            return
    install_apache_httpd()
    stop_apache()
    esg_functions.stream_subprocess_output("chkconfig --levels 2345 httpd off")
    install_mod_wsgi()
    make_python_eggs_dir()
    copy_apache_conf_files()
    start_apache()


if __name__ == '__main__':
    main()
