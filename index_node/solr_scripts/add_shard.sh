#!/bin/sh
# shell script to add a new Solr shard
#
# example invocation: add_shard.sh master 8984
# example invocation: add_shard.sh esgf-node.llnl.gov 8985
#
# note: this script is idempotent: it can be run multiple times without affecting the shard installation

# exit when a command fails
set -o errexit

# exit if any pipe commands fail
set -o pipefail

# command line arguments
shard_name=$1
shard_port=$2
shard="$1-$2"

# create index directory /esg/solr-index/<host>-<port>/
mkdir -p /esg/solr-index/${shard}
chown -R solr:solr /esg/solr-index/${shard}

# create solr-home directory /usr/local/solr-home/<host>-<port>/
if [ ! -d "$SOLR_HOME/${shard}" ]; then
  echo "Installing Solr shard: $shard"

  cp -R /usr/local/src/solr-home $SOLR_HOME/${shard}
  rm -rf $SOLR_HOME/${shard}/mycore

  # configure each core
  cores=("datasets"  "files"  "aggregations")
  for core in "${cores[@]}"
  do
    echo "Installing Solr core: $core"
    cp -R /usr/local/src/solr-home/mycore $SOLR_HOME/${shard}/${core}
    sed -i 's/@mycore@/'${core}'/g' $SOLR_HOME/$shard/$core/core.properties && \
    sed -i 's/@solr_config_type@-@solr_server_port@/'${shard}'/g' $SOLR_HOME/${shard}/${core}/core.properties
    if ! [[ $shard_name == 'master' || $shard_name == 'slave' ]]; then
       sed -i '/masterUrl/ s/localhost:8984/'${shard_name}'/' $SOLR_HOME/${shard}/${core}/conf/solrconfig.xml
    fi
  done
  chown -R solr:solr $SOLR_HOME/${shard}

fi

# add shard to list queried by ESGF search application (unless shard = 'master' or 'slave')
if ! [[ $shard_name == 'master' || $shard_name == 'slave' ]]; then
  shards_file="/esg/config/esgf_shards_static.xml"
  if ! grep -q ${shard_port} ${shards_file} ; then
    echo "Adding shard to ${shards_file}"
    # note: must work around the error: "sed: cannot rename /esg/config/sedFvmijX: Device or resource busy"
    sed 's/<\/shards>/    <value>localhost:'${shard_port}'\/solr<\/value>\n<\/shards>/g' ${shards_file} > ${shards_file}.new
    # call "/bin/cp" since for root cp is aliased to "cp -i" (which asks for confirmation)
    /bin/cp -f ${shards_file}.new ${shards_file}
  fi
fi
