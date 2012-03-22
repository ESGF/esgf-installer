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
#   source /usr/local/esgf/installer/esg-purge.sh && esg-purge
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
    if [ X"$1" = "X" ] ; then
        PURGEMODE="default"
    else
        PURGEMODE=$1
    fi
    case $PURGEMODE in
    default)
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
        echo "Unrecognized purge mode '${PURGEMODE}', aborting!"
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
    rm -f /etc/esg.env
    rm -rf /usr/local/esgf-dashboard-ip
    # The glob may fail here with no targets, thus || true
    rm -rf /usr/local/esgf-solr-* || true
}

esg-purge-cdat () {
    rm -rf /usr/local/cdat
}

esg-purge-globus () {
    rm -rf /etc/grid-security
    rm -rf $HOME/.globus
    rm -rf /root/.globus
    rm -rf /usr/local/globus
    rm -rf /usr/local/gsoap
}

esg-purge-las () {
    rm -rf /usr/local/ferret
    rm -rf /usr/local/ferret_data
    # The glob may fail here with no targets, thus || true
    rm -rf /usr/local/las-esg-* || true
}

esg-purge-postgres () {
    # esg-node --stop may not actually cause Postgresql to exit
    # properly, so force-kill all remaining instances
    pkill -9 -u postgres
    rm -rf /usr/local/pgsql

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
}

esg-purge-workbench() {
    rm -rf /usr/local/src/esgf/workbench
}
