#!/bin/bash

#####
# ESG SECURITY
# This script is intended to be an adjunct to the esg-node / esg-gway scripts
#             (author: gavin@llnl.gov)
#****************************************************************************
#*                                                                          *
#*  Organization: Lawrence Livermore National Lab (LLNL)                    *
#*   Directorate: Computation                                               *
#*    Department: Computing Applications and Research                       *
#*      Division: S&T Global Security                                       *
#*        Matrix: Atmospheric, Earth and Energy Division                    *
#*       Program: PCMDI                                                     *
#*       Project: Earth Systems Grid (ESG) Data Node Software Stack         *
#*  First Author: Gavin M. Bell (gavin@llnl.gov)                            *
#*                                                                          *
#****************************************************************************
#*                                                                          *
#*   Copyright (c) 2009, Lawrence Livermore National Security, LLC.         *
#*   Produced at the Lawrence Livermore National Laboratory                 *
#*   Written by: Gavin M. Bell (gavin@llnl.gov)                             *
#*   LLNL-CODE-420962                                                       *
#*                                                                          *
#*   All rights reserved. This file is part of the:                         *
#*   Earth System Grid (ESG) Data Node Software Stack, Version 1.0          *
#*                                                                          *
#*   For details, see http://esgf.org/                                      *
#*   Please also read this link                                             *
#*    http://esgf.org/LICENSE                                               *
#*                                                                          *
#*   * Redistribution and use in source and binary forms, with or           *
#*   without modification, are permitted provided that the following        *
#*   conditions are met:                                                    *
#*                                                                          *
#*   * Redistributions of source code must retain the above copyright       *
#*   notice, this list of conditions and the disclaimer below.              *
#*                                                                          *
#*   * Redistributions in binary form must reproduce the above copyright    *
#*   notice, this list of conditions and the disclaimer (as noted below)    *
#*   in the documentation and/or other materials provided with the          *
#*   distribution.                                                          *
#*                                                                          *
#*   Neither the name of the LLNS/LLNL nor the names of its contributors    *
#*   may be used to endorse or promote products derived from this           *
#*   software without specific prior written permission.                    *
#*                                                                          *
#*   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS    *
#*   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT      *
#*   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS      *
#*   FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL LAWRENCE    *
#*   LIVERMORE NATIONAL SECURITY, LLC, THE U.S. DEPARTMENT OF ENERGY OR     *
#*   CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,           *
#*   SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT       *
#*   LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF       *
#*   USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND    *
#*   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,     *
#*   OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT     *
#*   OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF     *
#*   SUCH DAMAGE.                                                           *
#*                                                                          *
#****************************************************************************
######


# Description: Installation of the esg-security infrastructure.  This
#              file is meant to be sourced by the esg-node
#              scripts that has the definition of checked_get(),
#              stop_tomcat(), start_tomcat(), $workdir,

workdir=${workdir:-${installer_home}/workbench/esg}
service_name=${service_name:-"thredds"}
extensions=${extensions:-".nc"}
exempt_extensions=${exempt_extensions:-".xml"}
exempt_services=${exempt_services:-"thredds/wms, thredds/wcs, thredds/ncss, thredds/ncml, thredds/uddc, thredds/iso, thredds/dodsC"}


def setup_access_logging_filter():
    esg_bash2py.mkdir_p(config["workdir"])
    with esg_bash2py.pushd(config["workdir"]):
        install_access_logging_filter()

    esg_tomcat_manager.start_tomcat()


def install_access_logging_filter(dest_dir="/usr/local/tomcat/webapps/thredds", esg_filter_entry_file="esg-access-logging-filter-web.xml"):
    '''Takes 2 arguments:
    dest_dir  - The top level directory of the webapp where filter is to be installed.
    esg_filter_entry_file - The file containing the filter entry xml snippet (optional: defaulted)

    Installs esg filter into ${service_name}'s web.xml file, directly after
    the AuthorizationTokenValidationFilter's mapping, by replacing a
    place holder token with the contents of the filter snippet file
    "esg-filter-web.xml".  Copies the filter jar file to the ${service_name}'s
    lib dir
    '''
    service_name = esg_bash2py.trim_string_from_head(dest_dir)
    esg_filter_entry_pattern = "<!--@@esg_access_logging_filter_entry@@-->"

    print "*******************************"
    print "Installing ESGF Node's Access Logging Filters To: [{}]".format()
    print "*******************************"
    print "Filter installation destination dir = {}".format(dest_dir)
    print "Filter entry file = {}".format(esg_filter_entry_file)
    print "Filter entry pattern = {}".format(esg_filter_entry_pattern)

    #pre-checking... make sure the files we need in ${service_name}'s dir are there....
    if not os.path.exists(os.path.join(dest_dir, "WEB-INF")):
        logger.error("WARNING: Could not find %s's installation dir - Filter Not Applied",service_name)
        return False
    if not os.path.exists(os.path.join(dest_dir, "WEB-INF", "lib")):
        logger.error("Could not find WEB-INF/lib installation dir - Filter Not Applied")
        return False
    if not os.path.exists(os.path.join(dest_dir, "WEB-INF", "lib")):
        logger.error("Could not find WEB-INF/lib installation dir - Filter Not Applied")
        return False
    if not os.path.exists(os.path.join(dest_dir, "WEB-INF", "web.xml")):
        logger.error("No web.xml file found for %s - Filter Not Applied", service_name)
        return False

    esg_tomcat_manager.stop_tomcat()

    get_mgr_libs(os.path.join(dest_dir, "WEB-INF", "lib"))

    if not esg_filter_entry_pattern in open(os.path.join(dest_dir, "WEB-INF", "web.xml")).read():
        logger.info("No Pattern Found In File [%s/WEB-INF/web.xml] - skipping this filter setup\n", dest_dir)
        return

    #TODO: break into separat function; extract esg_filter_entry_file from jar
    esg_functions.download_update(os.path.join(config["workdir"], "esgf-node-manager-common-1.0.1.jar"), "https://aims1.llnl.gov/esgf/dist/2.6/0/esgf-node-manager/esgf-node-manager-common-1.0.1.jar")
    esg_functions.download_update(os.path.join(config["workdir"], "esgf-node-manager-filters-1.0.1.jar"), "https://aims1.llnl.gov/esgf/dist/2.6/0/esgf-node-manager/esgf-node-manager-filters-1.0.1.jar")
    with esg_bash2py.pushd(config["workdir"]):
        with zipfile.ZipFile("esgf-node-manager-filters-1.0.1.jar", 'r') as zf:
            #Pull out the templated filter entry snippet file...
            zf.extract(esg_filter_entry_file)
        #going to need full path for pattern replacement below
        esg_filter_entry_file_path = os.path.join(os.getcwd(), esg_filter_entry_file)

        #Place (copy) the filter jar in the WEB-INF/lib
        print "Installing ESGF Node Manager Filter jar..."
        shutil.copyfile("esgf-node-manager-common-1.0.1.jar", os.path.join(dest_dir, "WEB-INF", "lib", "esgf-node-manager-common-1.0.1.jar"))
        shutil.copyfile("esgf-node-manager-filters-1.0.1.jar", os.path.join(dest_dir, "WEB-INF", "lib", "esgf-node-manager-filters-1.0.1.jar"))

    with esg_bash2py.pushd(os.path.join(dest_dir, "WEB-INF")):


install_access_logging_filter() {

    #----------------------
    #${service_name}'s configuration...
    pushd ${dest_dir}/WEB-INF >& /dev/null
    [ $? != 0 ] && echo " WARNING: Could not find the ${service_name} web application (${tomcat_install_dir}/webapps/${service_name}/)" && return 0
    local target_file=web.xml

    #Replace the filter's place holder token in ${service_name}'s web.xml file with the filter entry.
    #Use utility function...
    insert_file_at_pattern $(readlink -f ${target_file}) ${esg_filter_entry_file} "${esg_filter_entry_pattern}"

    #Edit the web.xml file for ${service_name} to include these token replacement values
    echo -n "Replacing tokens... "
    eval "perl -p -i -e 's/\\@service.name\\@/${service_name}/g' ${target_file}"; echo -n "*"
    eval "perl -p -i -e 's/\\@exempt_extensions\\@/${exempt_extensions}/g' ${target_file}"; echo -n "*"
    eval "perl -p -i -e 's#\\@exempt_services\\@#${exempt_services}#g' ${target_file}"; echo -n "*"
    eval "perl -p -i -e 's/\\@extensions\\@/${extensions}/g' ${target_file}"; echo -n "*"
    echo " [OK]"
    popd >& /dev/null
    #----------------------
    chown -R ${tomcat_user} ${dest_dir}/WEB-INF
    chgrp -R ${tomcat_group} ${dest_dir}/WEB-INF

    return 0
}

get_mgr_libs() {
    echo "Checking for / Installing required jars..."

    node_manager_app_home=${node_manager_app_home:-"${CATALINA_HOME}/webapps/esgf-node-manager"}

    local dest_dir=${1:-${tomcat_install_dir}/webapps/${service_name}/WEB-INF/lib}
    local src_dir=${node_manager_app_home}/WEB-INF/lib

    ([ ! -d ${dest_dir} ] || [ ! -d ${src_dir} ]) && echo "WARNING: source and/or destination dir(s) not present!!! (punting)" && return 1

    #Jar versions...
    local commons_dbcp_version=${commons_dbcp_version:-1.4}
    local commons_dbutils_version=${commons_dbutils_version:-1.3}
    local commons_pool_version=${commons_pool_version:-1.5.4}

    #----------------------------
    #Jar Libraries Needed To Be Present For Node Manager (AccessLogging) Filter Support
    #----------------------------
    local dbcp_jar=commons-dbcp-${commons_dbcp_version}.jar
    local dbutils_jar=commons-dbutils-${commons_dbutils_version}.jar
    local pool_jar=commons-pool-${commons_pool_version}.jar
    local postgress_jar=${postgress_jar:-postgresql-9.4-1201.jdbc41.jar}

    #move over libraries...
    echo "getting (copying) libary jars from the Node Manager App to ${dest_dir} ..."

    [ ! -e ${dest_dir}/${dbcp_jar} ]      && cp -v ${src_dir}/${dbcp_jar}      ${dest_dir}
    [ ! -e ${dest_dir}/${dbutils_jar} ]   && cp -v ${src_dir}/${dbutils_jar}   ${dest_dir}
    [ ! -e ${dest_dir}/${pool_jar} ]      && cp -v ${src_dir}/${pool_jar}      ${dest_dir}
    [ ! -e ${dest_dir}/${postgress_jar} ] && cp -v ${src_dir}/${postgress_jar} ${dest_dir}


    #----------------------------
    #Fetching Node Manager Jars from Distribution Site...
    #----------------------------

    #values inherited from esg-node calling script
    local node_manager_commons_jar=esgf-node-manager-common-${esgf_node_manager_version}.jar
    local node_manager_filters_jar=esgf-node-manager-filters-${esgf_node_manager_version}.jar

    echo "getting (downloading) library jars from Node Manager Distribution Server to ${dest_dir} ..."
    local make_backup_file=0 #Do NOT make backup file
    checked_get ${dest_dir}/${node_manager_commons_jar} ${esg_dist_url}/esgf-node-manager/${node_manager_commons_jar} $((force_install)) $((make_backup_file))
    checked_get ${dest_dir}/${node_manager_filters_jar} ${esg_dist_url}/esgf-node-manager/${node_manager_filters_jar} $((force_install)) $((make_backup_file))


    #remove all other node manager jars that are not what we want
    echo "cleaning up (removing) other, unnecessary, Node Manager project jars from ${dest_dir} ..."
    rm -vf $(/bin/ls ${dest_dir}/${node_manager_commons_jar%-*}-*.jar | grep -v ${esgf_node_manager_version})
    rm -vf $(/bin/ls ${dest_dir}/${node_manager_filters_jar%-*}-*.jar | grep -v ${esgf_node_manager_version})
    #---

    chown -R ${tomcat_user}:${tomcat_group} ${dest_dir}

}
