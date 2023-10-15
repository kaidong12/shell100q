#!/bin/sh

###############################################################################
# This script is for configuring TruCQ
###############################################################################

source ./common.sh
source ./common_env.sh

NoPerr_exit() {
  echo $1 | $TO
  echo "Please contact support for further assistance." | $TO
  echo "Exiting..." | $TO
  echo "Install log is located at $LOG_FILE"
  exit 1;
} 

valid_ip()
{
  local  ip=$1
  ip_stat=1

  if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    # Old Internal Field Separator
    OIFS=$IFS
    # Internal Field Separator
    IFS='.'
    ip=($ip)
    IFS=$OIFS
    [[ ${ip[0]} -le 255 && ${ip[1]} -le 255 \
        && ${ip[2]} -le 255 && ${ip[3]} -le 255 ]]
    ip_stat=$?
  fi
}


echo "Configure database" | $TO
# ???? cp -f truviso /etc/init.d


#Get DB Port
while true; do
  read -p "Enter TruCQ Port (5432)" ans
  if [ -z $ans ]; then
    ans="5432"
  fi
  ./checkPort.sh $ans
  if [ $? -eq 0 ]; then
    break
  fi
  echo "Port is not free or invalid. Valid ports are 1 through 65535"
done
PGPORT=$ans


PGDATAROOT=/var/opt
if [ "$HA" = "true" ]; then
  PGDATAROOT="/trucq-a"
fi
while true; do
    read -p "Enter TruCQ root data directory ($PGDATAROOT)" ans
    if [ "$ans" = "" ]
    then
	 
        break
    fi
    if [ -e "$ans" ]
    then
        export PGDATAROOT=$ans
	
        break
    else
        echo "$ans doesn't exist"
    fi
done
PGDATABASE=$PGDATAROOT/primea
PGDATA=$PGDATABASE/data
#set default that may be updated later
PGHOST='localhost'



#
# Configure /etc/sysconfig/primeanalytics/trucq
#
echo "sysconfig file: $SYSCONFIG_FULLPATH"  | $TO

#March 11 NOP - IS NOW primea
#echo "TEMP, what about rc.d ...?"
#pushd $SYSCONFIG
#mv -f primea trucq
#popd
#echo "END TEMP"
#END NOP


pushd $SYSCONFIG  > /dev/null
sed '$a\
TRULINK_APP='$TRUVISO_HOME'/app \
PGPORT='$PGPORT' \
PGHOST='$PGHOST' \
BIDBHOST='$PGHOST' \
BIDBPORT='$PGPORT' \
PGDATA='$PGDATA' \
PA_HOME='$PA_HOME' \
ANT_HOME='$PA_HOME/thirdparty/apache-ant-1.7.1' \
JAVA_HOME='$PA_HOME/thirdparty/$JDK' \
HA='$HA' \
IBIP='$IBIP' \
CQLOG='$PGDATABASE'/trucq.log' < $SYSCONFIG_FILE > /tmp/base_a1_22x11.txt
if [ $? -ne 0 ]; then
        err_exit "Fatal error updating sysconfig $SYSCONFIG_FULLPATH"
fi
sed "/TRUVISO_HOME=/c\TRUVISO_HOME=$TRUVISO_HOME" /tmp/base_a1_22x11.txt  > /tmp/a11_22x11.txt
if [ "$INSTALL_TYPE" = "all" ] || [ "$INSTALL_TYPE" = "bip" ]; then
sed '$a\
BIPLATFORM_HOME='$PA_HOME'/biplatform' < /tmp/a11_22x11.txt > /tmp/base_a1_22x111.txt
cp -f /tmp/base_a1_22x111.txt /tmp/a11_22x11.txt
fi
cp -f /tmp/a11_22x11.txt $SYSCONFIG_FILE
if [ $? -ne 0 ]; then
        err_exit "Fatal error final updating sysconfig $SYSCONFIG_FULLPATH"
fi


cat ${SYSCONFIG_FILE}
echo "-------------------------"
popd  > /dev/null





chkconfig --add $DB_SERVICE_NAME
STATUS=$?
if [ $STATUS -ne 0 ]; then
        err_exit "Fatal error add $DB_SERVICE_NAME"
fi 

# temp reference export PA_USER=primea
# temp reference export SYSCONFIG=/etc/sysconfig/primeanalytics
# temp reference export DB_SERVICE_NAME=trucq


chkconfig $DB_SERVICE_NAME on
STATUS=$?
if [ $STATUS -ne 0 ]; then
        err_exit "Fatal error $DB_SERVICE_NAME chkconfig on"
fi 
service $DB_SERVICE_NAME initdb
STATUS=$?
if [ $STATUS -ne 0 ]; then
        err_exit "Fatal error initdb $DB_SERVICE_NAME"
fi 
service $DB_SERVICE_NAME start
STATUS=$?
if [ $STATUS -ne 0 ]; then
        err_exit "Fatal error can't start database", errno $STATUS
fi 
echo "Database started" | $TO

if [ "$INSTALL_TYPE" != "db" ]; then
   echo "Configure database completed" | $TO
   exit 0
fi



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
service $DB_SERVICE_NAME restart
if [ $STATUS -ne 0 ]; then
        echo "Error restarting $DB_SERVICE_NAME"
        echo "Please contact support for further assistance."
        echo "Exiting..."
        exit 1;
fi

echo "Configure database completed" | $TO









