import os
import zipfile
import logging
import yaml
import requests
from clint.textui import progress
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py


with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)



#!/bin/bash

#####
# ESG SEARCH
# This script is intended to be an adjunct to the esg-node script
#             (author: gavin@llnl.gov)
#****************************************************************************
#*                                                                          *
#*  Organization: Lawrence Livermore National Lab (LLNL)                    *
#*   Directorate: Computation                                               *
#*    Department: Computing Applications and Research                       *
#*      Division: S&T Global Security                                       *
#*        Matrix: Atmospheric, Earth and Energy Division                    *
#*       Program: PCMDI                                                     *
#*       Project: Earth Systems Grid Fed (ESGF) Node Software Stack         *
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
#*   Earth System Grid Fed (ESGF) Node Software Stack, Version 1.0          *
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


# Description: Installation of the esg-search submodule.  This
#              file is meant to be sourced by the esg-node
#              script that has the definition of checked_done(), dedup(),
#              ${workdir}, etc....


DEBUG=${DEBUG:-0}
VERBOSE=${VERBOSE:-0}

#--------------
#User Defined / Settable (public)
#--------------
install_prefix=${install_prefix:-"/usr/local"}
esg_solr_user=${SOLR_USER:-"solr"}
esg_solr_group=${SOLR_GROUP:-"solr"}
esg_functions_file=${install_prefix}/bin/esg-functions
esg_root_dir=${esg_root_dir:-"/esg"}
esg_config_dir=${esg_config_dir:-"${esg_root_dir}/config"}
tomcat_install_dir=${tomcat_install_dir:-${CATALINA_HOME:=${install_prefix}/tomcat}}
workdir=${workdir:-~/workbench/esg}
install_manifest=${install_manifest:-"${esg_root_dir}/esgf-install-manifest"}
esgf_shards_config_file=${esg_config_dir}/esgf_shards.config
esgf_shards_static_file=${esg_config_dir}/esgf_shards_static.xml
esgf_shards_dynamic_file=${esg_config_dir}/esgf_shards.xml
esgf_excludes_file=${esg_config_dir}/esgf_excludes.txt

esgf_publisher_resources_home=${esgf_publisher_resources_home:-${esgf_config_dir}}
esgf_publisher_resources_repo=${esgf_publisher_resources_repo:-https://github.com/ESGF/esgf-publisher-resources.git}
#--------------

date_format=${date_format:-"+%Y_%m_%d_%H%M%S"}
compress_extensions=${compress_extensions:-".tar.gz|.tar.bz2|.tgz|.bz2"}
force_install=${force_install:-0}

installer_uid=${installer_uid:-$(id ${HOME##*/} | sed 's/.*uid=\([0-9]*\).*/\1/')}
[ $? != 0 ] || [ -z "$installer_uid" ] && echo "installer_uid is not set" && exit 1
installer_gid=${installer_gid:-$(id ${HOME##*/} | sed 's/.*gid=\([0-9]*\).*/\1/')}
[ $? != 0 ] || [ -z "$installer_gid" ] && echo "installer_gid is not set" && exit 1
installer_home=${HOME}

esg_search_version=${esg_search_version:-"1.2.0"}
search_install_dir=${ESGF_INSTALL_DIR:-"${install_prefix}/esgf_search"}
seach_data_dir=${ESGF_DATA_DIR:="${esg_root_dir}/search_data"}
esgf_crawl_launcher="esgf-crawl"
esgf_index_optimization_launcher="esgf-optimize-index"

if [ ! -e ${esg_functions_file} ]; then
    checked_get ${esg_functions_file} ${esg_dist_url}$( ((devel == 1)) && echo "/devel" || echo "")/esgf-installer/${esg_functions_file##*/} $((force_install))
    [ ! -s "${esg_functions_file}" ] && rm ${esg_functions_file}
fi
[ -e ${esg_functions_file} ] && source ${esg_functions_file} && ((VERBOSE)) && printf "sourcing from: ${esg_functions_file} \n"

if [ -e /etc/esg.install_log ] && [ ! -e "${install_manifest}" ]; then
    echo "migrating install manifest to new location"
    mv -v /etc/esg.install_log  ${install_manifest}
fi

#---------------------------------------------------------
# The "main" method for this script
#---------------------------------------------------------
#arg (1) - install = 0 [default]
#          upgrade = 1
# The other args are a list of <hostname>:<port> of all the replica indexes you wish to create
setup_search() {
    echo
    echo "*******************************"
    echo "Setting up The ESGF Search Sub-Project..."
    echo "*******************************"
    echo

    local upgrade=${1:-0}
    shift
    solr_config_types=$@
    #check for solr user and group existence; create if necessary
    id $esg_solr_user
    if [ $? != 0 ]; then
        echo " WARNING: There is no solr user \"$esg_solr_user\" present on system"
        #NOTE: "useradd/groupadd" are a RedHat/CentOS thing... to make this cross distro compatible clean this up.
        if [ ! $(getent group ${esg_solr_group}) ]; then
            /usr/sbin/groupadd -r ${esg_solr_group}
            [ $? != 0 ] && [ $? != 9 ] && echo "ERROR: Could not add solr system group: ${esg_solr_group}" && popd && checked_done 1
        fi
        echo "/usr/sbin/useradd -r -c"SOLR User" -g $esg_solr_group $esg_solr_user"
        /usr/sbin/useradd -r -c"SOLR User" -g $esg_solr_group $esg_solr_user
        [ $? != 0 ] && [ $? != 9 ] && echo "ERROR: Could not add SOLR system account user \"$esg_solr_user\"" && popd && checked_done 1
    fi
    #setup_zookeeper && configure_zookeeper && write_zookeeper_install_log
    #[ $? != 0 ] && echo " ERROR: Could not fully install zookeeper :-( " && checked_done 1

    debug_print "solr_config_types = ${solr_config_types}"
    for config_type in $solr_config_types; do
        echo "Doing setup and configuration for ${config_type}"
        add_shard ${config_type}
        [ $? != 0 ] && echo " ERROR: Could not fully install solr :-( " && checked_done 1
    done

    setup_search_service ${upgrade} && write_search_service_install_log
    [ $? != 0 ] && echo " ERROR: Could not fully install search service" && checked_done 1

    write_as_property index_service_endpoint "http://${esgf_host:-$(hostname --fqdn)}/esg-search/search"
    write_as_property index_service_app_home ${search_web_service_dir}
    write_as_property index_master_port
    write_as_property index_slave_port
    write_as_property index_timeout_connection 2000
    write_as_property index_timeout_read_datasets 10000
    write_as_property index_timeout_read_files 60000

    write_as_property publishing_service_endpoint "https://${esgf_host:-$(hostname --fqdn)}/esg-search/remote/secure/client-cert/hessian/publishingService"
    write_as_property publishing_service_app_home ${search_web_service_dir}

    write_search_rss_properties

    setup_publisher_resources
    [ $? != 0 ] && echo " WARNING: Could not setup publisher resources" || echo " [OK] "
    write_as_property esgf_publisher_resources_home
    write_as_property esgf_publisher_resources_repo

    #Get utility script for crawling thredds sites
    fetch_crawl_launcher
    fetch_index_optimization_launcher

    echo "done"
    echo
    return 0
}

setup_publisher_resources() {
    echo "Publisher Resources... (${esgf_publisher_resources_repo})"
    [[ ! ${esg_config_dir} ]] && echo "WARNING: No Configuration directory set - Cannot setup publisher resources [FAIL]" && return 1
    [ ! -d "${esgf_publisher_resources_home:=${esg_config_dir}}" ] && mkdir -p ${esgf_publisher_resources_home}
    #local found_git=$(type git | sed -e 's/.*(\([^)]*\))/\1/') #this incantation works on for the output of 'type' on macs... not on CentOS
    local found_git=${git_install_dir}/bin/git
    [ ! -e "${found_git}" ] && found_git=$(type git | awk '{print $3}')
    [[ ! ${found_git} ]] && return 2 || ((DEBUG)) && echo "git found: ${found_git}"
    local repo_tld=${esgf_publisher_resources_home}/$(sed -e 's/.git//' <<<${esgf_publisher_resources_repo##*/})
    if [ -d "${repo_tld}/.git" ]; then
        (cd ${repo_tld} && ${found_git} fetch --all && ${found_git} pull) || return 3
    else
        ((DEBUG)) && echo "${found_git} clone ${esgf_publisher_resources_repo} ${repo_tld}"
        ${found_git} clone ${esgf_publisher_resources_repo} ${repo_tld} 2> /dev/null || return 4
    fi
}

search_startup_hook() {
    echo "Search Startup Hook... :-)"
    get_property index_auto_fetch_pub_resources
    [ -z "${index_auto_fetch_pub_resources}" ] && index_auto_fetch_pub_resources="true" && write_as_property index_auto_fetch_pub_resources
    [ "$(tr [A-Z] [a-z] <<<${index_auto_fetch_pub_resources})" = "true" ] && setup_publisher_resources
}

#--------------------
# ONE SHOT FUNCTIONS (called from outside this script [see esg-node's options])
#--------------------

#--------------------
#Does a full sanity check of the configuration
# Here are the checks (7 points)
# - That it is in the esgf_shards.config file [<hostname>:<port>] (it always is)
#
# (next does not apply to master)
# - That the corresponding entry is in the esgf_shards_static.xml file ["localhost":<port>] (all but the master needs to be listed here)
#
# (next does not apply to slave nor master)
# - That the corresponding entry is in the esgf_excludes.txt file [<hostname> INDEX] (this is so that replicated shards are not dyn added)
#
# (all)
# - That there is a corresponding installation directory /usr/local/solr<version>/<hostname>-<port>
#
# (next two not needed for local slave and master)
# - That within that directory the entry is present and correct in EACH of the core solrconfig.xml files <hostname>:8983 (where the remote master is)
# - That within that directory the entry for cores are present and configured in the solr.xml <hostname>-<port> inserted in xml.
#
# (all)
# - That there is data directory for physically storing the index in /esg/solr-index/<hostname-<port>
#----------------------
# These critera map to the "*"|"-" values listed.  If anything is incorrect then there is an "X" displayed.
# "*" = present and accounted for
# "-" = not applicable
# "X" = problem
#
# Ex: (Everything all good)
#
# %> esg-node --check-shards
#      Checking configuration of shards...
#      slave @ 8983: **-*--* [PASS]
#      master @ 8984: *--*--* [PASS]
#      esg-datanode.jpl.nasa.gov @ 8985: ******* [PASS]
#      pcmdi11.llnl.gov @ 8986: ******* [PASS]
#      pcmdi9.llnl.gov @ 8987: ******* [PASS]
#--------------------
check_shards() {
    echo "Checking configuration of shards..."
    local shards=( $(_load_shards_config) )
    for ((i=0; i < ${#shards[@]}; i++)); do
        local bad=0
        solr_init ${shards[i]}
        echo -n "${solr_config_type} @ ${solr_server_port}: "
        [ -n "$(sed -n 's/.*'${solr_config_type}':'${solr_server_port}'.*/&/p' ${esgf_shards_config_file})" ] && echo -n "*" || echo -n "X"
        if [ "${solr_config_type}" != "master" ]; then
            [ -n "$(sed -n 's/.*localhost:'${solr_server_port}'.*/&/p' ${esgf_shards_static_file})" ] && echo -n "*" || echo -n "X"
        else
            echo -n "-"
        fi
        if [ "${solr_config_type}" != "master" ] && [ "${solr_config_type}" != "slave" ]; then
            [ -n "$(sed -n 's/.*'${solr_config_type}'.*INDEX.*/&/pI' ${esgf_excludes_file})" ] && echo -n "*" || echo -n "X"
        else
            echo -n "-"
        fi
        if [ -e "${solr_install_dir}" ]; then
            echo -n "*"
            if [ "${solr_config_type}" != "master" ] && [ "${solr_config_type}" != "slave" ]; then
                if (( $(sed -n 's/.*masterUrl.*'${solr_config_type}':'80'.*/&/p' ${solr_install_dir}/*/conf/solrconfig.xml | wc -l) == ${#solr_cores[@]} )); then
                    echo -n "*"
                else
                    echo -n "X"
                    echo "check the files: ${solr_install_dir}/*/conf/solrconfig.xml"
                    ((bad++))
                fi
            else
                echo -n "-"
                echo -n "-"
            fi
        else
            echo -n "X"
            ((bad++))
        fi
        if [ -e "${solr_data_dir}" ]; then
            echo -n "*"
            echo -n " $(du -sh ${solr_data_dir} | awk '{print $1}')"
        else
            echo -n "X"
            ((bad++))
        fi
        (( bad == 0 )) && echo -n " [PASS]" || echo -n " [FAIL]"
        nc -zi 1 localhost ${solr_server_port} >& /dev/null && echo " [RUNNING]" || echo "[NOT RUNNING]"
    done
    echo
}

add_shard() {
    local config_type=${1:?"Must specify shard host or type"}
    local target_index_search_port=80
    if [ "${config_type%:*}" != "master" ] && [ "${config_type%:*}" != "slave" ]; then
        if grep -q ${config_type%:*} ${esgf_shards_config_file} ; then
            local answer="y"
            echo " A replica shard entry for ${config_type%:*} is already present!"
            read -p " Are you sure you wish to add a NEW replica index for ${config_type%:*}? [Y/n] " answer
            [ -z "${answer}" ] || [ "$(tr A-Z a-z <<< ${answer})" = "n" ] && return 1
        fi
        if ! curl -f -s -m 5 http://${config_type%:*}:${target_index_search_port}/solr >& /dev/null ; then
            local answer="n"
            echo "WARNING the shard source entered [${config_type%:*}] is not currently reachable"
            read -p "Would you like to continue anyway [y/N]? " answer
            [ -z "${answer}" ] || [ "$(tr A-Z a-z <<< ${answer})" = "n" ] && return 1
        fi
        nc -w 3 -z ${config_type%:*} ${target_index_search_port} 2> /dev/null || echo "[INFO] - The search port [${target_index_search_port}] is not available on ${config_type%:*}"
    fi
    setup_solr ${config_type} && configure_solr ${config_type} && write_solr_install_log && _commit_configuration
}

remove_shard() {
    [ -z "${1}" ] && echo "no shard specified" && return 1
    _remove_replica_shard_configuration ${1}
}

list_local_shards() {
    _dedup_shards_config
    cat ${esgf_shards_config_file}
}

init_all_shards() {
    for shard_spec in $(list_local_shards); do
        add_shard $shard_spec
    done
}

#--------------------
# Private utility functions
#--------------------
_load_shards_config() {
    [ ! -e "${esgf_shards_config_file}" ] && echo "Sorry no esgf shards configuration file found: ${esgf_shards_config_file}" && return 0
    _dedup_shards_config
    cat ${esgf_shards_config_file} | sed '/^#.*/d' | xargs
}

_commit_configuration() {

    #Put the entry in the shards configuration file, if not already there
    #note: grep returns true [0] if it can make a match
    grep -q ${solr_config_type}:${solr_server_port} ${esgf_shards_config_file} && echo "${esgf_shards_config_file}: entry already present" || \
        echo "${solr_config_type}:${solr_server_port}" >> ${esgf_shards_config_file}

    #Check the static shards file (esgf_shards_static.xml)
    #First, if it is not there, go fetch it...
    if [ ! -e "${esgf_shards_static_file}" ]; then
        _curl "${esg_dist_url}/esg-search/${esgf_shards_static_file##*/}" "${esgf_shards_static_file}"
    fi
    #Do NOT need to write an entry into the static shards file in am the master index
    if [ "${solr_config_type}" != "master" ]; then
        if [ -n "$(sed -n 's/localhost:'${solr_server_port}'/&/p' ${esgf_shards_static_file})" ]; then
            echo "${esgf_shards_static_file}: entry is already present"
        else
            #-------------------------------------------------------
            #TODO: This should be done as single compound sed statement not 3 separate edits
            #-------------------------------------------------------
            #remove myself from the static shards list...
            sed -i '/'${esgf_host:-$(hostname --fqdn)}':8983/Id' ${esgf_shards_static_file}

            #remove the replicated shard's hostname:port entry from STATIC shards file...
            sed -i '/'${solr_config_type}':8983/Id' ${esgf_shards_static_file}

            #remove the replicated shard's hostname:port entry from DYNAMIC shards file...
            sed -i '/'${solr_config_type}':8983/Id' ${esgf_shards_static_file%_*}.xml

            #Put the Entry in for this local replica index of the remote index @ ${solr_config_type}
	    if [ ${solr_server_port} != 8983 ]; then
            	sed -i '/<[/]shards>/i \ <value>localhost:'${solr_server_port}'/solr</value>' ${esgf_shards_static_file}
	    fi
        fi
    fi

    #Check the esgf_excludes.txt file to see if entry is already there
    #Do NOT need entries if are your own shards (master or slave)
    if [ "${solr_config_type}" != "master" ] && [ "${solr_config_type}" != "slave" ]; then
        grep -q ${solr_config_type} ${esgf_excludes_file} && echo "${esgf_excludes_file}: entry already present" || echo "${solr_config_type} INDEX" >> ${esgf_excludes_file}
    fi
}

#Input arg1 - hostname:port
_remove_replica_shard_configuration() {

    local configured_ports
    local remote_host
    local local_port
    read remote_host local_port <<< $(awk -F : '{print $1" "$2}' <<< ${1})

    if [ "${remote_host}" = "master" ] || [ "${remote_host}" = "slave" ]; then
        echo "WARNING: You may not remove master or slave indexes with this method"
        return 0
    fi

    #If the port value is empty... let's try to pick the best one...
    configured_ports=($(sort -u ${esgf_shards_config_file} | sed -n 's/'${remote_host}'/&/p' | awk -F ':' '{print $2}' | xargs))
    if [ -z "${local_port}" ]; then
        if (( ${#configured_ports[@]} == 1 )); then
            local_port=${configured_ports[0]}
        else
            (( ${#configured_ports[@]} == 0 )) && echo "Do not have an appropriate entry for ${remote_host}" && return 1
            (( ${#configured_ports[@]} > 1 ))  && echo "Multiple ports configured for ${remote_host} [ ${configured_ports[@]} ], you must explicitly specify port: (${remote_host}:<port>)" && return 2
        fi
    fi

    ! grep -q "${remote_host}:${local_port}" ${esgf_shards_config_file} && echo "Must select one of the configured port(s): [${configured_ports[@]}]" && return 1

    solr_init "${remote_host}:${local_port}"
    if [ "${solr_config_type}" = "master" ] || [ "${solr_config_type}" = "slave" ]; then
        echo "WARNING: You may not remove master or slave indexes with this method."
        return 0
    fi
    local answer="n"
    read -p "Are you sure you wish to remove replica index for ${solr_config_type}:${solr_server_port}? [y/N] " answer
    [ -z "${answer}" ] || [ "$(tr A-Z a-z <<< ${answer})" = "n" ] && return 1

    echo "Removing replica shard configuration for ${solr_config_type} on port ${solr_server_port}... "
    #Remove the entries in the config files
    #esgf_shards.config
    debug_print "Removing entry from: ${esgf_shards_config_file}"
    sed -i.bak '/.*'${solr_config_type}':'${solr_server_port}'.*/d' ${esgf_shards_config_file}

    #esgf_shards_static.xml
    debug_print "Removing entry from: ${esgf_shards_static_file}"
    sed -i.bak '/.*localhost:'${solr_server_port}'.*/d' ${esgf_shards_static_file}

    #esgf_excludes.txt
    (( ${#configured_ports[@]} > 1 )) || sed -i.bak -e '/.*'${solr_config_type}'.*index.*/Id' ${esgf_excludes_file}

    local pid
    if pid=$(pgrep -f jetty.port=${solr_server_port}); then
        echo -n "Stopping index procees for this shard ${remote_host} [pid = ${pid}] "
        ${solr_server_dir}/bin/solr stop -p ${solr_server_port}
        pgrep -f jetty.port=${solr_server_port} >& /dev/null && echo "[FAIL] - unable to stop solr server on port ${solr_server_port}" || echo "[OK] "
    else
        echo "no process found for [pid = ${pid}] "
    fi

    #Remove the configuration directory
    debug_print "rm -rf ${solr_install_dir}"
    rm -rf ${solr_install_dir}

    #Remove the data (index) itself w/ cores
    debug_print "rm -rf ${solr_data_dir}"
    rm -rf ${solr_data_dir}
    echo "[REMOVED]"
}

_is_port_taken() {
    local suggested_port=${1:?"Requires <port> as argument"}
    local no_use_ports=($(cat <(netstat -ant | grep LISTEN | awk '{print $4}' | sed -n 's/.*:\(.*\)/\1/p' | sort -n -u) <(awk -F ':' '{print $2}' ${esgf_shards_config_file}) | sort -n -u ))
    if [ -n "$(echo ${no_use_ports[@]} | sed -n 's/\b'${suggested_port}'\b/&/p')" ]; then
        #true (yes, it is taken)
        return 0
    else
        #false (no the port is NOT taken, available)
        return 1
    fi
}

_get_next_open_port() {
    local start_port=${1:-$(sort -t ':' -u -k2,2 ${esgf_shards_config_file} | tail -1 | awk -F ':' '{print $2}')}
    local suggested_port=${start_port}
    local no_use_ports=($(cat <(netstat -ant | grep LISTEN | awk '{print $4}' | sed -n 's/.*:\(.*\)/\1/p' | sort -n -u) <(awk -F ':' '{print $2}' ${esgf_shards_config_file}) | sort -n -u ))
    for ((i=0; i < 100; i++)); do
        if [ -n "$(echo ${no_use_ports[@]} | sed -n 's/\b'${suggested_port}'\b/&/p')" ]; then
            ((suggested_port++))
        else
            break
        fi
    done
    echo ${suggested_port}
}

#--------------------
# Lifecycle functions
#--------------------

start_search_services() {
    echo "Starting search services... $@"
    if [ -e "${esg_config_dir}/facets.properties" ]; then
        #check the format and version to determine if should move aside.
        #Not the best sed regex..."#v." passes :-(
        #Don't know how to do an "at least one" greedy match, usually '+' would do it.
        if [ -z "$(sed '/^$/d' ${esg_config_dir}/facets.properties | head -n1 | sed -n '/^#[ ]*v[0-9]*\.[0-9]*[ ]*$/p')" ]; then
            echo "Detected an old style or out of version file [${esg_config_dir}/facets.properties] moving it out of the way..."
            mv -v ${esg_config_dir}/facets.properties{,.bak}
        fi
    fi

    if [ ! -e "${esg_config_dir}/facets.properties" ] && [ -e "${tomcat_install_dir}/webapps/esg-search/WEB-INF/classes/esg/search/config/facets.properties" ]; then
        cp -v ${tomcat_install_dir}/webapps/esg-search/WEB-INF/classes/esg/search/config/facets.properties ${esg_config_dir}/facets.properties
    fi
    #start_zookeeper
    start_solr $(_load_shards_config)
}

stop_search_services() {
    echo "Stopping search services..."
    stop_solr $(_load_shards_config)
    #stop_zookeeper
}



#---------------------------------------------------------
# Solr Search Service Setup and Configuration
#---------------------------------------------------------

tomcat_install_dir=${tomcat_install_dir:-${install_prefix}/tomcat}
web_app_tld=${tomcat_install_dir}/webapps

search_web_service_name=esg-search
search_web_service_dir=${web_app_tld}/${search_web_service_name}
search_service_dist_url=${esg_dist_url}/${search_web_service_name}/${search_web_service_name}-${esg_search_version}.tar.gz

#####
# Install The Search Service...
#####
# - Takes boolean arg: 0 = setup / install mode (default)
#                      1 = updated mode
#
# In setup mode it is an idempotent install (default)
# In update mode it will always pull down latest after archiving old
#

def check_esg_search_version():


def setup_search_service():

setup_search_service() {
    echo -n "Checking for search service ${esg_search_version}"
    check_webapp_version "esg-search" ${esg_search_version}
    local ret=$?
    ((ret == 0)) && (( ! force_install )) && echo " [OK]" && return 0

    echo
    echo "*******************************"
    echo "Setting up The ESGF Search Service..."
    echo "*******************************"
    echo

    local upgrade=${1:-0}

    local default="Y"
    ((force_install)) && default="N"
    local dosetup
    if [ -d ${search_web_service_dir} ]; then
        echo "Detected an existing search service installation..."
        read -p "Do you want to continue with search services installation and setup? $([ "$default" = "N" ] && echo "[y/N]" || echo "[Y/n]") " dosetup
        [ -z "${dosetup}" ] && dosetup=${default}
        if [ "${dosetup}" != "Y" ] && [ "${dosetup}" != "y" ]; then
            echo "Skipping search service installation and setup - will assume it's setup properly"
            return 0
        fi

        local dobackup="Y"
        read -p "Do you want to make a back up of the existing distribution?? [Y/n] " dobackup
        [ -z "${dobackup}" ] && dobackup=${default}
        if [ "${dobackup}" = "Y" ] || [ "${dobackup}" = "y" ]; then
            echo "Creating a backup archive of this web application ${search_web_service_dir}"
            backup ${search_web_service_dir}
        fi

        echo
    fi

    mkdir -p ${workdir}
    [ $? != 0 ] && return 1
    pushd ${workdir} >& /dev/null
    local fetch_file


    local search_service_dist_file=${search_service_dist_url##*/}
    #strip off .tar.gz at the end
    #(Ex: esg-search-1.0.1.tar.gz -> esg-search-1.0.1)
    local search_service_dist_dir=$(echo ${search_service_dist_file} | awk 'gsub(/('$compress_extensions')/,"")')

    checked_get ${search_service_dist_file} ${search_service_dist_url} $((force_install))
    no_new_update=$?

    if((upgrade)); then
        ((no_new_update == 1)) && echo "nothing more to do, you are up2date" && return 1
        echo "Upgrading the ESG Search Service..."
        rm -rf ${search_service_dist_dir}
    fi

    echo "unpacking ${search_service_dist_file}... in $(pwd)"
    tar xzf ${search_service_dist_file}
    [ $? != 0 ] && echo " ERROR: Could not extract the ESG Search Service: ${search_service_dist_file}" && popd && checked_done 1

    pushd ${search_service_dist_dir} >& /dev/null

    stop_tomcat


    #strip the version number off(#.#.#) the dir and append .war to get the name of war file
    #(esg-search-x.x.x -> esg-search.war)
    local trimmed_name=${search_service_dist_dir%-*}
    local search_service_war_file=$(pwd)/${trimmed_name}.war
    echo "search_service_war_file = "${search_service_war_file}

    #----------------------------
    #make room for new install
    set_aside_web_app ${search_web_service_dir}
    #----------------------------

    mkdir -p ${search_web_service_dir}
    [ $? != 0 ] && echo "Could not create dir ${search_web_service_dir}" && popd >& /dev/null && checked_done 1
    cd ${search_web_service_dir}

    echo "Expanding war ${search_service_war_file} in $(pwd)"
    $JAVA_HOME/bin/jar xf ${search_service_war_file}
    set_aside_web_app_cleanup ${search_web_service_dir} $?

    # update Solr schema.xml file
    echo "Checking for Solr schema update"

    new_solr_xml=${search_web_service_dir}/WEB-INF/solr-home/mycore/conf/schema.xml
    echo "up-to-date Solr schema: ${new_solr_xml}"

    solr_home_dir="${localhost-8982}/solr-home"
    solr_shards=(master-8984 localhost-8982)
    solr_cores=(datasets files aggregations)

    # loop over shards
    for ((j=0;j<${#solr_shards[@]};j++)) ; do

       # loop over solr cores
       for ((i=0;i<${#solr_cores[@]};i++)) ; do

	    old_solr_xml="/usr/local/solr-home/${solr_shards[${j}]}/${solr_cores[${i}]}/conf/schema.xml"
	    #echo "Checking ${old_solr_xml}"
	    if [ -e  ${old_solr_xml} ]; then
	      if diff ${old_solr_xml} ${new_solr_xml} >/dev/null ; then
	  	    echo "Files: ${old_solr_xml}, ${new_solr_xml} are identical, not upgrading"
	      else
	  	    echo "cp ${new_solr_xml} ${old_solr_xml}"
	  	    cp ${new_solr_xml} ${old_solr_xml}
	      fi
	    fi

       done

    done


    chown -R ${tomcat_user}  ${search_web_service_dir}
    chgrp -R ${tomcat_group} ${search_web_service_dir}
    popd >& /dev/null
    #----------------------------
    (( ! upgrade ))
    checked_done 0

}

write_search_service_install_log() {
    echo "$(date ${date_format}) webapp:esg-search=${esg_search_version} ${search_web_service_dir}" >> ${install_manifest}
    dedup ${install_manifest}
    return 0
}


#---------------------------------------------------------
# Solr/Lucene Setup and Configuration
#---------------------------------------------------------

#Input param <hostname>[:<port>]
solr_init() {
    get_property index_master_port "8984"
    get_property index_slave_port "8983"

    solr_version=5.5.5
    #solr_dist_url=${esg_dist_url}/thirdparty/apache-solr-${solr_version}.tgz
    # http://archive.apache.org/dist/lucene/solr/5.2.1/solr-5.2.1.tgz
    solr_dist_url=http://archive.apache.org/dist/lucene/solr/${solr_version}/solr-${solr_version}.tgz
    solr_workdir=${workdir}/solr-${solr_version}
    echo "Using solr_workdir=${solr_workdir}"

    #The install of solr pivots on this variable
    #make this config type "sticky"
    read solr_config_type solr_server_port <<< $(awk -F : '{print $1" "$2}' <<< ${1})
    [ "${solr_config_type}" = "master" ] && [ -z "${solr_server_port}" ] && solr_server_port=${index_master_port}
    [ "${solr_config_type}" = "slave" ]  && [ -z "${solr_server_port}" ] && solr_server_port=${index_slave_port}
    if [ -z "${solr_server_port}" ]; then
        local suggested_port=$(_get_next_open_port)
        echo "[INFO] - You have not selected a local port value for the index serving the ${solr_config_type} replica... Will use ${suggested_port}"
        solr_server_port=${suggested_port}
    fi

    solr_install_dir=${install_prefix}/solr-home/${solr_config_type}-${solr_server_port}
    echo "Using solr_install_dir=${solr_install_dir}"

    solr_data_dir=${esg_root_dir}/solr-index/${solr_config_type}-${solr_server_port}
    echo "Using solr_data_dir=${solr_data_dir}"

    #solr_server_dir=${install_prefix}/solr-${solr_version}
    solr_server_dir=${install_prefix}/solr
    echo "Using solr_server_dir=${solr_server_dir}"

    solr_logs_dir=${esg_root_dir}/solr-logs
    echo "Using solr_logs_dir=${solr_logs_dir}"

    # SOLR JAVA MEMORY - defaults to 512m
    # example: export SOLR_HEAP=1g
    SOLR_HEAP="${SOLR_HEAP:-512m}"

    echo "Using esg_dist_url=${esg_dist_url}"
    solr_cores=(datasets files aggregations)
    debug_print "init: ${solr_config_type} [${solr_server_port}]"
}

#Input param <hostname>[:<port>]
setup_solr() {
    solr_init ${1}
    echo
    echo -n "Checking for solr ${solr_version}... "
    (cd ${solr_install_dir} >& /dev/null; ls ${solr_cores[@]} >& /dev/null) && [ -e ${solr_server_dir}/server/start.jar ] && check_solr_version
    [ $? == 0 ] && (( ! force_install )) && echo " [OK]" && return 0

    echo
    echo "*******************************"
    echo "Setting up (ESGF) Solr... ${solr_version} ${solr_config_type} on port ${solr_server_port}"
    echo "*******************************"
    echo

    local dosetup
    if [ -x ${solr_server_dir}/server/start.jar ]; then
        echo "Detected an existing solr-home installation for ${solr_config_type} configuration type..."
        read -p "Do you want to continue with solr-home installation and setup? [y/N] " dosetup
        if [ "${dosetup}" != "Y" ] && [ "${dosetup}" != "y" ]; then
            echo "Skipping solr-home installation and setup - will assume solr-home is setup properly"
            return 0
        fi
        echo
    fi

    if [ -n "$(awk -F ':' '{print $2}' ${esgf_shards_config_file} | sort -u | sed -n 's/'${solr_server_port}'/&/p')" ]; then
        local answer="n"
        echo " A replica shard entry for port [${solr_server_port}] is already present!"
        read -p " Are you sure you wish to add a NEW replica index for ${solr_config_type%:*} on port [${solr_server_port}]? [y/N] " answer
        [ -z "${answer}" ] || [ "$(tr A-Z a-z <<< ${answer})" = "n" ] && return 1
    fi

    echo "Installing solr-home ${solr_config_type} on port[${solr_server_port}]..."
    mkdir -p ${solr_workdir}
    pushd ${solr_workdir} >& /dev/null

    local solr_dist_file=${solr_dist_url##*/}
    local solr_dist_dir=$(echo ${solr_dist_file} | awk 'gsub(/('$compress_extensions')/,"")')

    #There is this pesky case of having a zero sized dist file... WTF!?
    if [ -e ${solr_dist_file} ]; then
        ((DEBUG)) && ls -l ${solr_dist_file}
        local size=$(stat -c%s ${solr_dist_file})
        (( size == 0 )) && rm -v ${solr_dist_file}
    fi

    #Check to see if we already have a solr distribution directory
    #if [ ! -e ${solr_install_dir} ]; then
        echo "Don't see solr installation dir ${solr_install_dir}"
        if [ ! -e ${solr_dist_file} ]; then
            echo "Don't see solr distribution file $(pwd)/${solr_dist_file} either"
            echo "Downloading solr from ${solr_dist_url}"
            #NOTE: should change this to call checked_get (but don't want to copy and paste that function here)
            #When I do the refactoring of some of the functions, then I can source that functions file and use checked_get.
            #For now just fetch it.
            checked_get ${solr_dist_file} ${solr_dist_url} $((force_install))
            (( $? > 1 )) && echo " ERROR: Could not download solr ${solr_dist_file} from ${solr_dist_url}" && popd && checked_done 1
            echo "unpacking ${solr_dist_file}... into $(pwd)"
            tar xzf ${solr_dist_file}
            [ $? != 0 ] && echo " ERROR: Could not extract solr [${solr_dist_file}] ... :-( " && popd && checked_done 1
        fi
    #fi

    #If you don't see the directory but see the tar.gz distribution
    #then expand it and go from there....
    if [ -e ${solr_dist_file} ] && [ ! -e ${solr_dist_dir} ]; then
        echo "unpacking* ${solr_dist_file} into $(pwd)"
        tar xzf ${solr_dist_file}
        [ $? != 0 ] && echo " ERROR: Could not extract solr [${solr_dist_file}] :-( " && popd && checked_done 1
    fi

    # move unpacked solr distribution to final location
    #if [ ! -e ${solr_server_dir} ]; then
    	pushd ${install_prefix} >& /dev/null

        echo "copying: ${solr_workdir}/solr-${solr_version} to: ${install_prefix}/solr-${solr_version}"
        cp -R ${solr_workdir}/solr-${solr_version} .
        rm -f ./solr
        ln -s ./solr-${solr_version} ./solr

        # override log4j.properties file
        wget ${esg_dist_url}/esg-search/etc/conf/solr/log4j.properties -O ${solr_server_dir}/server/resources/log4j.properties
        mkdir -p ${solr_logs_dir}

        # change owner:group
        chown -R ${esg_solr_user}:${esg_solr_group} solr-${solr_version}
        chown -R ${esg_solr_user}:${esg_solr_group} $(readlink -f ${solr_server_dir})
        chown -R ${esg_solr_user}:${esg_solr_group} ${solr_logs_dir}

        popd >& /dev/null
    #fi

    [ -d ${solr_install_dir} ] && (echo "Backing up previous install... " && (backup ${solr_install_dir} || (mv ${solr_install_dir}{,.bak} || echo "Could not move aside prev install")))
    [ ! -d "${solr_install_dir}" ] && echo "Creating installation dir: ${solr_install_dir}" && mkdir -p ${solr_install_dir}

    # create solr cores
    pushd ${solr_workdir} >& /dev/null
  	rm -rf solr-home*
    echo 'Downloading ${esg_dist_url}/esg-search/solr-home.tar'
    wget ${esg_dist_url}/esg-search/solr-home.tar
    tar xvf solr-home.tar
    cp -R solr-home/* ${solr_install_dir}/.
    popd >& /dev/null

    local err_count=0
    cd ${solr_install_dir}
    for ((i=0;i<${#solr_cores[@]};i++)) ; do
        if [ ! -e  ${solr_install_dir}/${solr_cores[${i}]} ]; then
        	echo "Creating core directory: ${solr_install_dir}/${solr_cores[${i}]}"
        	cp -R mycore ${solr_cores[${i}]}
		    core_file=${solr_cores[${i}]}/core.properties
		    sed --in-place 's/@mycore@/'${solr_cores[${i}]}'/g' ${core_file}
		    sed --in-place 's/@solr_config_type@/'${solr_config_type}'/g' ${core_file}
		    sed --in-place 's/@solr_server_port@/'${solr_server_port}'/g' ${core_file}
            [ $? != 0 ] && echo "Could not install core: ${solr_cores[${i}]} - no exemplar found" && ((err_count++)) && continue
        fi
        echo "core: ${solr_cores[${i}]} - [OK]"
    done
    ((err_count == 0)) && rm -rf ${solr_install_dir}/mycore
    echo "${solr_version}" > ${solr_install_dir}/VERSION


    (($DEBUG)) && echo "chown -R ${esg_solr_user}:${esg_solr_group} ${solr_install_dir}"
    chown    ${esg_solr_user}:${esg_solr_group} "$(dirname "${solr_install_dir}")"
    chown -R ${esg_solr_user}:${esg_solr_group} $(readlink -f "$(dirname "${solr_install_dir}")")

    popd >& /dev/null
    echo -n "solr-home setup "
    (( err_count == 0 )) && echo "[OK]" && return 0
    (( (err_count > 0) && (err_count < ${#solr_cores[@]}) )) && echo "[PARTIAL]" && return 1
    (( err_count == ${#solr_cores[@]} )) && echo "[FAIL]" && return 2
}


#TODO: change these curls to either get certs to use ssl or use checked_get
#Input param <hostname>[:<port>]
configure_solr() {

    solr_init ${1} >& /dev/null
    echo -n "Configuring solr... ${solr_config_type} port[${solr_server_port}] "

    pushd ${solr_install_dir} >& /dev/null
    local suffix
    if [ ! "${solr_config_type}" = "master" ] && [ ! "${solr_config_type}" = "slave" ]; then


 		# configure replication handler for all cores
 		for ((i=0;i<${#solr_cores[@]};i++)) ; do
 			echo "Configuring replication handler for ${hostname}:${solr_server_port}"
 			solr_config_file=${solr_cores[${i}]}/conf/solrconfig.xml
 			# NOTE: replicates from port 80
			sed --in-place 's/localhost:8984/'${solr_config_type}:80'/g' ${solr_config_file}
 			sed --in-place 's/00:00:60/'01:00:00'/g' ${solr_config_file}
 		done
    fi

    #------------------------
    # Create the data (index) directories
    #------------------------
    eval mkdir -p $(echo ${solr_data_dir}/{${solr_cores[@]}} | sed 's/ /,/g')
    chown -R ${esg_solr_user}:${esg_solr_group} $(readlink -f "$(dirname "${solr_data_dir}")")

    popd >& /dev/null
    echo " [OK]"
    return 0

}

#-----
#"private functions"
#-----

#Using curl straight up won't give you any signal that you are not
#getting the file... so we have to buffer and inspect it manually
#first.
_curl() {
    verbose_print "${1} > ${2}"
    local content=$(curl -s -L --insecure ${1})
    grep -q 404 <<< $content && echo "ERROR: [404] could not download ${1}" && return 1
    echo "$content" > ${2}
}

_dedup_solr_realm() {
    local infile=${1:-${envfile}}
    [ ! -e "${infile}" ] && echo "WARNING: dedup_solr_realm() - unable to locate ${infile} does it exist?" && return 1
    [ ! -w "${infile}" ] && echo "WARNING: dedup_solr_realm() - unable to write to ${infile}" && return 1
    local tmp=$(tac ${infile} | awk 'BEGIN {FS="[ :]"} !($1 in a) {a[$1];print $0}' | sort -k1,1)
    echo "$tmp" > ${infile}
}

_dedup_shards_config() {
    local infile=${1:-${esgf_shards_config_file}}
    [ ! -e "${infile}" ] && echo "WARNING: dedup_shards_config() - unable to locate ${infile} does it exist?" && return 1
    [ ! -w "${infile}" ] && echo "WARNING: dedup_shards_config() - unable to write to ${infile}" && return 1
    local tmp=$(tac ${infile} | awk 'BEGIN {FS="[ :]"} !($2 in a) {a[$2];print $0}' | sort -t ':' -k2,2)
    echo "$tmp" > ${infile}
}




def write_search_rss_properties():
    node_short_name = esg_property_manager.get_property("node.short.name")
    esgf_feed_datasets_title = node_short_name + " RSS"
    esgf_feed_datasets_desc = "Datasets Accessible from node: {}".format(node_short_name)
    esgf_feed_datasets_link = "http://{}/thredds/catalog.html".format(esg_functions.get_esgf_host())

    esg_property_manager.set_property("esgf_feed_datasets_title", esgf_feed_datasets_title)
    esg_property_manager.set_property("esgf_feed_datasets_desc", esgf_feed_datasets_desc)
    esg_property_manager.set_property("esgf_feed_datasets_link", esgf_feed_datasets_link)


def fetch_crawl_launcher():
    esgf_crawl_launcher = "esgf-crawl"
    with esg_bash2py.pushd(config["scripts_dir"]):
        esgf_crawl_launcher_url = "https://aims1.llnl.gov/esgf/dist/devel/esg-search/esgf-crawl"
        esg_functions.download_update(esgf_crawl_launcher, esgf_crawl_launcher_url)
        os.chmod(esgf_crawl_launcher, 0755)

def fetch_index_optimization_launcher():
    with esg_bash2py.pushd(config["scripts_dir"]):
        esgf_index_optimization_launcher = "esgf-optimize-index"
        esgf_index_optimization_launcher_url = "https://aims1.llnl.gov/esgf/dist/devel/esg-search/esgf-optimize-index"
        esg_functions.download_update(esgf_index_optimization_launcher, esgf_index_optimization_launcher_url)
        os.chmod(esgf_index_optimization_launcher, 0755)

def fetch_static_shards_file():
    static_shards_file = "esgf_shards_static.xml"
    static_shards_url = "https://aims1.llnl.gov/esgf/dist/devel/lists/esgf_shards_static.xml"
    esg_functions.download_update(static_shards_file, static_shards_url)


def download_esg_search_war(esg_search_war_url):
    print "\n*******************************"
    print "Downloading ESG Search war file"
    print "******************************* \n"

    r = requests.get(esg_search_war_url, stream=True)
    path = '/usr/local/tomcat/webapps/esg-search/esg-search.war'
    with open(path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()

def setup_esg_search():
    '''Setting up the ESG Search application'''

    print "\n*******************************"
    print "Setting up ESG Search"
    print "******************************* \n"

    ESGF_REPO = "http://aims1.llnl.gov/esgf"
    esg_bash2py.mkdir_p("/usr/local/tomcat/webapps/esg-search")
    esg_search_war_url = "{ESGF_REPO}/dist/esg-search/esg-search.war".format(ESGF_REPO=ESGF_REPO)
    download_esg_search_war(esg_search_war_url)
    #Extract esg-search war
    with esg_bash2py.pushd("/usr/local/tomcat/webapps/esg-search"):
        with zipfile.ZipFile("/usr/local/tomcat/webapps/esg-search/esg-search.war", 'r') as zf:
            zf.extractall()
        os.remove("esg-search.war")

    TOMCAT_USER_ID = esg_functions.get_tomcat_user_id()
    TOMCAT_GROUP_ID = esg_functions.get_tomcat_group_id()
    esg_functions.change_ownership_recursive("/usr/local/tomcat/webapps/esg-search", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

def main():
    setup_esg_search()

if __name__ == '__main__':
    main()
