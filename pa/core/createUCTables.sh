#!/bin/sh

######################################################################
# Main script for master installer
######################################################################
source ./common.sh
source ./common_env.sh
source $SYSCONFIG_FULLPATH

#create tables for UsageCollection
TRUCQ_CONNECT_STRING="-h $TRUVISO_IP -p $PGPORT -U $DB_USER"
echo $TRUCQ_CONNECT_STRING
    psql  $TRUCQ_CONNECT_STRING < usagecollection.sql >>$LOG_FILE 2>&1
    if [ $? -ne 0 ]; then
    	err_exit "Fatal error executing UsageCollection.sql"
    fi
echo "Create database for UsageCollection completed."
