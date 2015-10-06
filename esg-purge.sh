#!/bin/sh
#
# esg-purge.sh
#
# This script is intended for sourcing, not direct execution.  It
# creates a series of esg-purge functions to return a system to a
# pre-install state and clears relevant environment variables.  (The
# environment variables will *only* be cleared from a source, not
# execution, which is why it is done this way).
#
# If you want to purge in a single command, you may wish to set up an
# alias to:
#   source /usr/local/esgf/installer/esg-purge.sh && esg-purge all
#
# Run the following command before running this script:
#   /usr/local/bin/esg-node --stop
#


# Clear relevant environment variables:
unset JAVA_HOME
unset PGHOME
unset PGHOST
unset PGPORT
unset PGUSER
unset X509_CERT_DIR
unset X509_USER_CERT
unset X509_USER_KEY

esg-purge () {
    PURGEMODE=$1
    case $PURGEMODE in
    fast|default)
        esg-purge-base
        esg-purge-cdat
        esg-purge-globus
        esg-purge-las
        esg-purge-postgres
        esg-purge-tomcat
        ;;
    all)
        # This part is the same as default
        esg-purge-base
        esg-purge-cdat
        esg-purge-globus
        esg-purge-las
        esg-purge-postgres
        esg-purge-tomcat
        # ... but we add ...
        esg-purge-utils
        esg-purge-workbench
        ;;
    cdat)
        esg-purge-cdat
        ;;
    globus)
        esg-purge-globus
        ;;
    las)
        esg-purge-las
        ;;
    more)
        # This part is the same as default
        esg-purge-base
        esg-purge-cdat
        esg-purge-globus
        esg-purge-las
        esg-purge-postgres
        esg-purge-tomcat
        # ... but we add ...
        esg-purge-workbench
        ;;
    postgres)
        esg-purge-postgres
        ;;
    thredds)
        esg-purge-thredds
        ;;
    tomcat)
        esg-purge-tomcat
        ;;
    tools)
        esg-purge-utils
        ;;
    workbench)
        esg-purge-workbench
        ;;
    *)
        echo "You must specify a valid purge mode!"
        echo "If you are doing a rebuild of the same version, you can try 'esg-purge fast'"
        echo "Otherwise, run 'esg-purge all'"
        return 1
        ;;
    esac
}

esg-purge-base () {
    # WARNING: ensure that any mounts are gone from /esg before this
    # stage.
    #
    # The default esg.ini file uses esg_dataroot, so we'll try
    # to unmount that first.  If esg.ini was changed, there may be
    # others.
    if [ -d /esg/gridftp_root/esg_dataroot ] ; then
        umount -f /esg/gridftp_root/esg_dataroot
    fi

    rm -rf /esg
    rm -rf /etc/certs
    rm -f /etc/esg.env
    rm -rf /etc/esgfcerts
    rm -f /etc/httpd/conf/esgf-httpd.conf
    rm -rf /etc/tempcerts
    rm -rf /opt/esgf
    rm -f /usr/local/bin/add_checksums_to_map.sh
    rm -rf /usr/local/cog
    rm -rf /var/www/.python-eggs

    rm -rf /tmp/inputpipe /tmp/outputpipe

    # WARNING: if $HOME has been reset from /root during an install
    # run, these directories could show up in a different place!
    rm -rf /root/.cache
    rm -rf /root/.python-eggs

    # These can potentially be symlinks back to git repositories for
    # development.  Remove only if they are regular files.
    find /usr/local/bin -type f -iname esg-\* -exec rm -f {} \+
    find /usr/local/bin -type f -iname esgf-\* -exec rm -f {} \+
    find /usr/local/bin -type f -iname setup-autoinstall -exec rm -f {} \+

    # The globs may fail here with no targets, thus || true
    rm -rf /usr/local/esgf* || true
    rm -rf /usr/local/esgf-solr-* || true
    rm -rf /usr/local/solr* || true
}

esg-purge-cdat () {
    yum remove -y cdat uvcdat
    rm -rf /usr/local/cdat /usr/local/uvcdat
}

esg-purge-globus () {
    yum remove -y globus\* myproxy\*
    rm -rf /etc/esgfcerts
    rm -f /etc/globus-host-ssl.conf
    rm -f /etc/globus-user-ssl.conf
    rm -f /etc/grid-security.conf
    rm -rf /etc/globus* || true
    rm -rf /etc/grid-security
    rm -rf /etc/gridftp* || true
    rm -f /etc/logrotate.d/globus-connect-server
    rm -rf /etc/myproxy* || true
    rm -rf /etc/pam.d/myproxy
    rm -f /etc/pam_pgsql.conf
    rm -f /etc/rc.d/init.d/globus-gridftp-* || true
    rm -rf $HOME/.globus
    rm -rf /root/.globus
    rm -rf /usr/local/globus
    rm -rf /usr/local/gsoap
    rm -rf /usr/share/myproxy
    rm -rf /var/lib/globus
    rm -rf /var/lib/globus-connect-server
    rm -rf /var/lib/myproxy
}

esg-purge-las () {
    rm -rf /usr/local/ferret
    rm -rf /usr/local/ferret_data
    # The glob may fail here with no targets, thus || true
    rm -rf /usr/local/las-esg* || true
}

esg-purge-postgres () {
    yum remove -y postgresql postgresql-libs postgresql-server \
        postgresql94 postgresql94-libs postgresql94-server postgresql94-devel

    # esg-node --stop may not actually cause Postgresql to exit
    # properly, so force-kill all remaining instances
    pkill -9 -u postgres
    rm -rf /usr/local/pgsql
    rm -rf /var/lib/pgsql

    # The installation of CDAT creates databases and tables, so
    # purging postgres but leaving CDAT will always result in invalid
    # assumptions on the part of the installer.
    esg-purge-cdat
}

esg-purge-thredds() {
    # Sometimes it's useful to purge just Thredds without purging all
    # of Tomcat
    rm -rf /usr/local/tomcat/webapps/thredds
}

esg-purge-tomcat () {
    # esg-node --stop may not actually cause Tomcat to exit properly,
    # so force-kill all remaining instances
    pkill -9 -u tomcat

    rm -f /etc/logrotate.d/esgf_tomcat

    # The glob may fail here with no targets, thus || true
    rm -rf /usr/local/tomcat* /usr/local/apache-tomcat* || true
}

esg-purge-utils () {
    # These are relatively safe elements that increase build time to clean
    rm -rf /usr/local/{ant,apache-ant-*}
    rm -rf /usr/local/curl
    rm -rf /usr/local/geoip
    rm -rf /usr/local/git
    rm -rf /usr/local/openssl
    rm -rf /usr/local/jdk1.*
    rm -f /usr/local/java
}

esg-purge-workbench() {
    rm -rf /usr/local/src/esgf/workbench
}
