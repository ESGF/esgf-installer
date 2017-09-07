import os
import subprocess
import shutil
import datetime
import socket
import shlex
import filecmp
import git
import esg_bash2py
import esg_version_manager
import esg_functions
import esg_logging_manager
import esg_init
import yaml
import pip


logger = esg_logging_manager.create_rotating_log(__name__)

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)


# # install latest apache httpd
# RUN yum -y update \
#     && yum install -y httpd httpd-devel mod_ssl \
#     && yum clean all
#
def install_python27():
    '''Install python with shared library '''
    with esg_bash2py.pushd("/tmp"):
        python_download_url = "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"

def install_apache_httpd():
    esg_functions.stream_subprocess_output("yum -y update")
    esg_functions.stream_subprocess_output("yum install -y httpd httpd-devel mod_ssl")
    esg_functions.stream_subprocess_output("yum clean all")

def install_mod_wsgi():
    '''Have to ensure python is install properly with the shared library for mod_wsgi installation to work'''
# # install mod_wsgi
# RUN cd /tmp
    pip.main(['install', "mod_wsgi==4.5.3"])
    with esg_bash2py.pushd("/etc/httpd/modules"):
        esg_bash2py.symlink_force("/usr/local/lib/python2.7/site-packages/mod_wsgi/server/mod_wsgi-py27.so", "/etc/httpd/modules/mod_wsgi-py27.so")

# RUN wget 'https://pypi.python.org/packages/c3/4e/f9bd165369642344e8fdbe78c7e820143f73d3beabfba71365f27ee5e4d3/mod_wsgi-4.5.3.tar.gz' && \
#     tar xvf mod_wsgi-4.5.3.tar.gz && \
#     cd mod_wsgi-4.5.3 && \
#     python setup.py install && \
#     rm -rf /tmp/mod_wsgi*
# RUN cd /etc/httpd/modules && \
#     ln -s /usr/local/lib/python2.7/site-packages/mod_wsgi-4.5.3-py2.7-linux-x86_64.egg/mod_wsgi/server/mod_wsgi-py27.so ./mod_wsgi-py27.so
#
def make_python_eggs_dir():
    esg_bash2py.mkdir_p("/var/www/.python-eggs")
    apache_user_id = esg_functions.get_user_id("apache")
    apache_group_id = esg_functions.get_group_id("apache")
    os.chown("/var/www/.python-eggs", apache_user_id, apache_group_id)
# # by default PYTHON_EGG_CACHE=/var/www/.python-eggs
# RUN mkdir -p /var/www/.python-eggs && \
#     chown -R apache:apache /var/www/.python-eggs
#
def copy_apache_conf_files():
    ''' Copy custom apache conf files '''
    shutil.copytree("apache_certs/", "/etc/certs/")
    shutil.copytree("apache_html/", "/var/www/html/")
    shutil.copyfile("apache_conf/httpd.conf", "/etc/httpd/conf.d/httpd.conf")
    shutil.copyfile("apache_conf/ssl.conf", "/etc/httpd/conf.d/ssl.conf")
# # configuration for standalone service
# # (overridden by ESGF settings when running with docker-compose from parent directory)
# COPY certs/ /etc/certs/
# COPY html/ /var/www/html/
# COPY conf/httpd.conf /etc/httpd/conf.d/httpd.conf
# COPY conf/ssl.conf /etc/httpd/conf.d/ssl.conf
#
# EXPOSE 80 443
#
# # start httpd server
# # parent process runs as 'root' to access port 80 and configuration files,
# # but it does NOT serve client requests
# # the child processes that serve user requests run as user 'apache'
# ADD conf/supervisord.httpd.conf /etc/supervisor/conf.d/supervisord.httpd.conf
# ADD scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
# ENTRYPOINT /usr/local/bin/docker-entrypoint.sh
def main():
    install_apache_httpd()
    install_mod_wsgi()
    make_python_eggs_dir()
    copy_apache_conf_files()


    # pass
if __name__ == '__main__':
    main()
