#!/bin/sh

source ./common.sh
source ./common_env.sh
source $SYSCONFIG_FULLPATH
NFSA=netflow_syslog_standalone_localFile-0520.tar.gz
NFNAMSYSLOGSA=netflow_namsyslog.tar.gz
EDRSTANDALONE=edr_standalone.tar.gz

NoPerr_exit() {
    echo $1 | $TO
    echo "Please contact support for further assistance." | $TO
    echo "Exiting..." | $TO
    echo "Install log is located at $LOG_FILE" 
    exit 1;
} 

function valid_ip()
{
    local  ip=$1
    ip_stat=1

    if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        OIFS=$IFS
        IFS='.'
        ip=($ip)
        IFS=$OIFS 
        [[ ${ip[0]} -le 255 && ${ip[1]} -le 255 \
            && ${ip[2]} -le 255 && ${ip[3]} -le 255 ]]
        ip_stat=$?
    fi
}




echo "Install Sample Data Generator for BI Platform, PORT $PGPORT" | $TO

SA_DIR=$PA_HOME/biplatform/sampledatagenerator
su bipuser -c "mkdir $SA_DIR"
STATUS=$?
if [ $STATUS -ne 0 ]; then
        err_exit "Error creating sampledatagenerator directory"
fi 


#cp syslog_standalone-0312.tar.gz $SA_DIR
cp $NFSA $SA_DIR
cp $NFNAMSYSLOGSA $SA_DIR
cp $EDRSTANDALONE $SA_DIR
pushd $SA_DIR > /dev/null
#su bipuser -c "tar -zxv --no-same-owner -f syslog_standalone-0312.tar.gz" >>$LOG_FILE 2>&1
su bipuser -c "tar -zxv --no-same-owner -f $NFSA" >>$LOG_FILE 2>&1
if [ $STATUS -ne 0 ]; then
        echo  "WARNING Error extracting sample $NFSA" | $TO
fi 
su bipuser -c "tar -zxv --no-same-owner -f $NFNAMSYSLOGSA" >>$LOG_FILE 2>&1
if [ $STATUS -ne 0 ]; then
        echo  "WARNING Error extracting sample $NFNAMSYSLOGSA" | $TO
fi 

su bipuser -c "tar -zxv --no-same-owner -f $EDRSTANDALONE" >>$LOG_FILE 2>&1
if [ $STATUS -ne 0 ]; then
        echo  "WARNING Error extracting sample $EDRSTANDALONE" | $TO
fi 


#
# Syslog SA Data Generator
if [ "$SL" = "SL" ]; then
pushd syslog_standalone > /dev/null

pushd customizations/instances > /dev/null

#get values to substitute for localhost:5432,  TRUVISO_IP:PGPORT
OLDIP=localhost
IP_PORT=${PGHOST}:${PGPORT}

#create_sample_datasource_postgresql.sql
sed "s/$OLDIP/$IP_PORT/"   < local-runtime.properties  > /tmp/a1_ipport22cql11.txt
cp -f /tmp/a1_ipport22cql11.txt local-runtime.properties
if [ $? -ne 0 ]; then
        err_exit "Fatal error updating Syslog local-runtime.properties"
fi
popd > /dev/null

su bipuser -c "./build-local.sh" >>$LOG_FILE 2>&1
STATUS=$?
if [ $STATUS -ne 0 ]; then
        err_exit "Error building syslog sample data"
fi

pushd customizations/db > /dev/null
psql -h $TRUVISO_IP -p $PGPORT -U $DB_USER < ddl.sql >>$LOG_FILE 2>&1
popd > /dev/null
popd > /dev/null
fi

#Update truviso templates

#get values to substitute for localhost:5432,  TRUVISO_IP:PGPORT
OLDIP=localhost
IP_PORT=${PGHOST}:${PGPORT}

sed "s/$OLDIP/$IP_PORT/"   < $TRUVISO_HOME/TruLink/template/customizations/instances/local-runtime.properties  > /tmp/a1_ipport22cql11.txt
cp -f /tmp/a1_ipport22cql11.txt $TRUVISO_HOME/TruLink/template/customizations/instances/local-runtime.properties
if [ $? -ne 0 ]; then
        err_exit "Fatal error updating TruLink local-runtime.properties"
fi

#EDR Build
pushd edr_standalone > /dev/null
STATUS=$?
if [ $STATUS -ne 0 ]; then
        read  -p "Error current directory is $PWD, press any key to continue"  dummy
        err_exit "Error accessing directory edr_standalone"
fi

pushd customizations/instances > /dev/null

#get values to substitute for localhost:5432,  TRUVISO_IP:PGPORT
OLDIP=localhost
IP_PORT=${PGHOST}:${PGPORT}

#create_sample_datasource_postgresql.sql
sed "s/$OLDIP/$IP_PORT/"   < local-runtime.properties  > /tmp/a1_ipport22cql11.txt
cp -f /tmp/a1_ipport22cql11.txt local-runtime.properties
if [ $? -ne 0 ]; then
        err_exit "Fatal error updating EDR local-runtime.properties"
fi
popd > /dev/null

su bipuser -c "./build-local.sh" >>$LOG_FILE 2>&1

STATUS=$?
if [ $STATUS -ne 0 ]; then
        err_exit "Error building EDR Standalone"
fi

popd > /dev/null

#
# NetFlow SA Data Generator
#
pushd netflow_syslog_standalone_localFile > /dev/null
STATUS=$?
if [ $STATUS -ne 0 ]; then
        read  -p "Error current directory is $PWD, press any key to continue"  dummy
        err_exit "Error accessing directory netflow_syslog_standalone_localFile"
fi
#temp patch
cp -f $TRUVISO_HOME/TruLink/template/stop.sh . &> /dev/null
cp -f $TRUVISO_HOME/TruLink/template/start.sh . &> /dev/null
#end patch 06/28
pushd customizations/instances > /dev/null

#get values to substitute for localhost:5432,  TRUVISO_IP:PGPORT
OLDIP=localhost
IP_PORT=${PGHOST}:${PGPORT}

#create_sample_datasource_postgresql.sql
sed "s/$OLDIP/$IP_PORT/"   < local-runtime.properties  > /tmp/a1_ipport22cql11.txt
cp -f /tmp/a1_ipport22cql11.txt local-runtime.properties
if [ $? -ne 0 ]; then
        err_exit "Fatal error updating Netflow local-runtime.properties"
fi
popd > /dev/null

su bipuser -c "./build-local.sh" >>$LOG_FILE 2>&1
STATUS=$?
if [ $STATUS -ne 0 ]; then
        err_exit "Error building NetFlow sample data"
fi


pushd customizations/db > /dev/null
# Done in Pentaho sql scripts psql -h $TRUVISO_IP -p $PGPORT -U $DB_USER < ddl.sql >>$LOG_FILE 2>&1
popd > /dev/null

popd > /dev/null



#
# NetFlow NAM SYSLOG SA
#
pushd netflow_namsyslog  > /dev/null
STATUS=$?
if [ $STATUS -ne 0 ]; then
        read  -p "Error current directory is $PWD, press any key to continue"  dummy
        err_exit "Error accessing directory netflow_namsyslog"
fi
#temp patch
cp -f $TRUVISO_HOME/TruLink/template/stop.sh . &> /dev/null
cp -f $TRUVISO_HOME/TruLink/template/start.sh . &> /dev/null
#end patch 06/28
pushd customizations/instances > /dev/null

#get values to substitute for localhost:5432,  TRUVISO_IP:PGPORT
OLDIP=localhost
IP_PORT=${PGHOST}:${PGPORT}

#create_sample_datasource_postgresql.sql
sed "s/$OLDIP/$IP_PORT/"   < local-runtime.properties  > /tmp/a1_ipport22cql11.txt
cp -f /tmp/a1_ipport22cql11.txt local-runtime.properties
if [ $? -ne 0 ]; then
        err_exit "Fatal error updating Netflow NAMSyslog local-runtime.properties"
fi
popd > /dev/null

su bipuser -c "./build-local.sh" >>$LOG_FILE 2>&1
STATUS=$?
if [ $STATUS -ne 0 ]; then
        err_exit "Error building NetFlow NAMSyslog"
fi


pushd customizations/db > /dev/null
# Done in Pentaho sql scripts psql -h $TRUVISO_IP -p $PGPORT -U $DB_USER < ddl.sql >>$LOG_FILE 2>&1
popd > /dev/null

popd > /dev/null




echo "Completed Installing Sample Data Generator for BI Platform" | $TO
exit 0


###++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++



while true; do
    read -p "Do you want to enable access from a remote client? (yes or no)" yn
    case $yn in
        [yes]* ) break;;
        [no]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

while true; do
    read -p "Enter IP Address of Remote Client " cip
    valid_ip $cip
    result=$ip_stat
    case $result in
        0 ) break;;
        * ) echo "Please enter valid IP Address.";;
    esac
done


echo "Enable remote access by client at $cip"



#####################################################


pushd $PGDATA > /dev/null
STATUS=$?
if [ $STATUS -ne 0 ]; then
        err_exit "Error $PGDATA
fi 
sed s/127.0.0.1/$cip/ <pg_hba.conf >/tmp/c-1-2.pg_hba.conf
STATUS=$?
if [ $STATUS -ne 0 ]; then
        echo "Error updating pg_hba.conf"
        echo "Please contact support for further assistance."
        echo "Exiting..."
        exit 1;
fi 
cp -f /tmp/c-1-2.pg_hba.conf pg_hba.conf
STATUS=$?
if [ $STATUS -ne 0 ]; then
        echo "Error copying pg_hba.conf"
        echo "Please contact support for further assistance."
        echo "Exiting..."
        exit 1;
fi
sed s/#listen_addresses\ \=\ \'localhost\'/listen_addresses\ \=\ \'*\'/ <postgresql.conf >/tmp/c-1-2.postgresql.conf
STATUS=$?
if [ $STATUS -ne 0 ]; then
        echo "Error updating postgresql.conf"
        echo "Please contact support for further assistance."
        echo "Exiting..."
        exit 1;
fi
cp -f /tmp/c-1-2.postgresql.conf postgresql.conf
STATUS=$?
if [ $STATUS -ne 0 ]; then
        echo "Error copying postgresql.conf"
        echo "Please contact support for further assistance."
        echo "Exiting..."
        exit 1;
fi
service truviso restart
if [ $STATUS -ne 0 ]; then
        echo "Error restarting truviso"
        echo "Please contact support for further assistance."
        echo "Exiting..."
        exit 1;
fi
echo "Done"  >> ${LOG_FILE}  2>&1









