#!/bin/sh

source ../../core/common.sh
source ../../core/common_env.sh
source $SYSCONFIG_FULLPATH


NoPerr_exit() {
    echo $1 | $TO
    echo "Please contact support for further assistance." | $TO
    echo "Exiting..." | $TO
    echo "Install log is located at $LOG_FILE" 
    exit 1;
} 


echo "Execute configure SQL Scripts for BI Platform, using IP $TRUVISO_IP, PORT $PGPORT" | $TO


#enter this script in sql directory
#

#get values to substitute for localhost:5432,  TRUVISO_IP:PGPORT
# Warning - Need standard pattern instead of testarossa6
OLDIP="testarossa6:5432"
IP_PORT="${TRUVISO_IP}:${PGPORT}"
#read -p "IP_PORT=${TRUVISO_IP}:${PGPORT} cont ..." dummy

#update_hibernate.sql
#first need to save/restore in case of reinstall
if [ -e .update_hibernate.sql ]; then
    cp -f .update_hibernate.sql update_hibernate.sql
fi
cp -f update_hibernate.sql .update_hibernate.sql
sed "s/$OLDIP/$IP_PORT/"   < update_hibernate.sql > /tmp/a1_ipport22cql11.txt
cp -f /tmp/a1_ipport22cql11.txt update_hibernate.sql
if [ $? -ne 0 ]; then
        err_exit "Fatal error updating update_hibernate.sql"
fi

#update_tvdb.sql
#first need to save/restore in case of reinstall
if [ -e .update_tvdb.sql ]; then
    cp -f .update_tvdb.sql update_tvdb.sql
fi
cp -f update_tvdb.sql .update_tvdb.sql
sed "s/$OLDIP/$IP_PORT/"   < update_tvdb.sql  > /tmp/a1_ipport22cql11.txt
cp -f /tmp/a1_ipport22cql11.txt update_tvdb.sql
if [ $? -ne 0 ]; then
        err_exit "Fatal error updating update_tvdb.sql"
fi


exit 0
