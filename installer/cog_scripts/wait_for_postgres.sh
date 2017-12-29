#!/bin/sh
# Script to wait untill connection to the Postgres container is ready

export PGPASSWORD=`cat /esg/config/.esg_pg_pass`

while ! psql -h esgf-postgres -U dbsuper -d esgcet -c "select 1" > /dev/null 2>&1; do
        echo 'Waiting for connection with postgres...'
        sleep 1;
done;
echo 'Connected to postgres...'
