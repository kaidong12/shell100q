#!/bin/sh

########################################################################################
# This script is for configuring TruCQ to be used for HA with BI Platform database
#
# 6/26 - change for services directory
#
########################################################################################

source ./common.sh
source ./common_env.sh
export BIDB_SERVICE_NAME=bitrucq


# For standalone instance of BI HA TruCQ instance
config_base_primea()
{
    pushd $SYSCONFIG  > /dev/null
    sed '$a\
TRULINK_APP='$TRUVISO_HOME'/app \
BIDBHOST='$BIDBHOST' \
BIDBPORT='$BIDBPORT' \
HA='$HA' \
IBIP='$IBIP' \
PA_HOME='$PA_HOME' \
ANT_HOME='$PA_HOME/thirdparty/apache-ant-1.7.1' \
JAVA_HOME='$PA_HOME/thirdparty/$JDK' ' < $SYSCONFIG_FILE > /tmp/base_a1_22x11.txt
    if [ $? -ne 0 ]; then
            err_exit "Fatal error updating BI HA sysconfig $SYSCONFIG_FULLPATH"
    fi
    sed "/TRUVISO_HOME=/c\TRUVISO_HOME=$TRUVISO_HOME" /tmp/base_a1_22x11.txt  > /tmp/a11_22x11.txt
    cp -f /tmp/a11_22x11.txt $SYSCONFIG_FILE
    if [ $? -ne 0 ]; then
            err_exit "Fatal error final updating BI HA sysconfig $SYSCONFIG_FULLPATH"
    fi
    popd > /dev/null
}

valid_ip()
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


echo "Configure BI HA database" | $TO

#Get DB Port
while true; do
  read -p "Enter TruCQ Port (5433)" ans
  if [ -z $ans ]; then
    ans="5433"
  fi
  ./checkPort.sh $ans
  if [ $? -eq 0 ]; then
    break
  fi
  echo "Port is not free or invalid. Valid ports are 1 through 65535"
done
BIDBPORT=$ans



# Get BI Platform DB directory on switched file system
PGDATAROOT="$SVCDIR/trucq-bi"
if [ ! -e "$PGDATAROOT" ]; then
   mkdir -p "$PGDATAROOT"
  if [ $? -ne 0 ]; then
        err_exit "Fatal error creating BI Platform database directory on switched file system: $PGDATAROOT"
  fi
fi


#may need this for other options.
#PGDATAROOT=/var/opt
#while true; do
    #read -p "Enter TruCQ root data directory (/var/opt)" ans
    #if [ "$ans" = "" ]
    #then
        #break
    #fi
    #if [ -e "$ans" ]
    #then
        #export PGDATAROOT=$ans
        #break
    #else
        #echo "$ans doesn't exist"
    #fi
#done
BIDBPGDATABASE=$PGDATAROOT/biprimea
BIDBPGDATA=$BIDBPGDATABASE/data
#set default that may be updated later
BIDBHOST='localhost'



#
# Configure /etc/sysconfig/primeanalytics/trucq
#

if [ "$INSTALL_TYPE" = "bidb" ]; then
    config_base_primea
fi

pushd $SYSCONFIG  > /dev/null
sed '$a\
BIDBPGDATA='$BIDBPGDATA' \
BIDBCQLOG='$BIDBPGDATABASE'/trucq.log' < $SYSCONFIG_FILE > /tmp/base_a1_22x11.txt
if [ $? -ne 0 ]; then
        err_exit "Fatal error updating sysconfig $SYSCONFIG_FULLPATH for BI Platform HA Database"
fi
sed "/BIDBPORT=/c\BIDBPORT=$BIDBPORT" /tmp/base_a1_22x11.txt  > /tmp/a11_22x11.txt
cp -f /tmp/a11_22x11.txt $SYSCONFIG_FILE
if [ $? -ne 0 ]; then
        err_exit "Fatal error final updating sysconfig $SYSCONFIG_FULLPATH for BI Platform HA Database"
fi


cat "${SYSCONFIG_FILE}"
echo "-------------------------"
popd  > /dev/null



cp -f bitrucq /etc/init.d

chkconfig --add $BIDB_SERVICE_NAME
STATUS=$?
if [ $STATUS -ne 0 ]; then
        err_exit "Fatal error add $BIDB_SERVICE_NAME"
fi 


chkconfig $BIDB_SERVICE_NAME on
STATUS=$?
if [ $STATUS -ne 0 ]; then
        err_exit "Fatal error $BIDB_SERVICE_NAME chkconfig on"
fi 

service $BIDB_SERVICE_NAME initdb
STATUS=$?
if [ $STATUS -ne 0 ]; then
        err_exit "Fatal error initdb $BIDB_SERVICE_NAME"
fi 


service $BIDB_SERVICE_NAME start
STATUS=$?
if [ $STATUS -ne 0 ]; then
        err_exit "Fatal error can't start BI HA database", errno $STATUS
fi 
echo "BI HA Database started" | $TO

if [ "$INSTALL_TYPE" != "db" ]; then
   echo "Configure BI HA database completed" | $TO
   exit 0
fi

echo "Configure BI HA database completed" | $TO
exit 0


# For HA only install on local node
#===========================================================


###############   Check if need to enable remote access  #############
read -p "You can enable a remote TruCQ client now or later. For information on managing remote TruCQ clients see the Prime Analytics Quick Start Guide. Press Enter to continue" dummy


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


echo "Enable remote database access from client at $cip" | $TO



#####################################################


pushd $PGDATA
STATUS=$?
if [ $STATUS -ne 0 ]; then
        err_exit "Error $PGDATA does not exist"
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
service $BIDB_SERVICE_NAME restart
if [ $STATUS -ne 0 ]; then
        echo "Error restarting $BIDB_SERVICE_NAME"
        echo "Please contact support for further assistance."
        echo "Exiting..."
        exit 1;
fi

echo "Configure database completed" | $TO









