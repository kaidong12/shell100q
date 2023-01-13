#!/bin/sh

###############################################################################
# This script is for configuring client access to a remote instance of TruCQ
###############################################################################



source ./common.sh
source ./common_env.sh

get_db_params() {
#  TRUVISO_IP,TRUVISO_PORT,DB_USER,DB_PASSWORD, BIDBHOST, BIDBPORT
      
      
  
# Get DB IP
    read -p "Enter IP address or hostname of TruCQ " ans
    TRUVISO_IP=$ans
      
# Get DB Port
    read -p "Enter TruCQ Port(5432)" ans
    if [ -z $ans ]; then
      ans="5432"
    fi
    TRUVISO_PORT=$ans

# Get DB User
#    read -p "Enter database username " ans
#    DB_USER=$ans
    DB_USER=$PA_USER

# Get DB Password
#    read -p "Enter database password " ans
#    DB_PASSWORD=$ans
     DB_PASSWORD=


   if [ $HA = "true" ] && [ "$INSTALL_TYPE" != "tl" ]; then
      read -p "Enter IP address or hostname of BI platform database " ans
      BIDBHOST=$ans

      read -p "Enter BI platform database Port(5432) " ans
      if [ -z $ans ]; then
           ans="5432"
      fi
      BIDBPORT=$ans
   else
       BIDBHOST=$TRUVISO_IP 
       BIDBPORT=$TRUVISO_PORT
   fi

}


check_db_connect() {
  DB=$1
  psql -h $TRUVISO_IP -p $TRUVISO_PORT -U $DB_USER -d $DB  < test.sql 2>&1 >/dev/null  | grep -q "FATAL"
  RESULT=$?   # grep will return 0 if it finds 'failure',  non-zero if it didn't 
  if [ $RESULT -eq 0 ]; then
      echo "DB User $DB_USER can't connect to DB [$DB] at $TRUVISO_IP Port $TRUVISO_PORT"
      return 1
  fi
  psql -h $TRUVISO_IP -p $TRUVISO_PORT -U $DB_USER -d $DB  < test.sql 2>&1 >/dev/null  | grep -q "could not connect to server"
  RESULT=$?   # grep will return 0 if it finds 'failure',  non-zero if it didn't 
  if [ $RESULT -eq 0 ]; then
      echo "DB User $DB_USER can't connect to DB [$DB] at $TRUVISO_IP Port $TRUVISO_PORT"
      return 1
  fi
  psql -h $TRUVISO_IP -p $TRUVISO_PORT -U $DB_USER -d $DB  < test.sql 2>&1 >/dev/null  | grep -q "service not known"
  RESULT=$?   # grep will return 0 if it finds 'failure',  non-zero if it didn't 
  if [ $RESULT -eq 0 ]; then
      echo "DB User $DB_USER can't connect to DB [$DB] at $TRUVISO_IP Port $TRUVISO_PORT -  Unknown Error"
      return 1
  fi

  # Additional checks if HA install
  if [ $HA = "true" ]; then

    psql -h $BIDBHOST -p $BIDBPORT -U $DB_USER -d $DB  < test.sql 2>&1 >/dev/null  | grep -q "FATAL"
    RESULT=$?   # grep will return 0 if it finds 'failure',  non-zero if it didn't 
    if [ $RESULT -eq 0 ]; then
      echo "DB User $DB_USER can't connect to BI platform database [$DB] at $BIDBHOST Port $BIDBPORT"
      return 1
    fi
    psql -h $BIDBHOST -p $BIDBPORT -U $DB_USER -d $DB  < test.sql 2>&1 >/dev/null  | grep -q "could not connect to server"
    RESULT=$?   # grep will return 0 if it finds 'failure',  non-zero if it didn't 
    if [ $RESULT -eq 0 ]; then
      echo "DB User $DB_USER can't connect to BI platform database [$DB] at $BIDBHOST Port $BIDBPORT"
      return 1
    fi
    psql -h $BIDBHOST -p $BIDBPORT -U $DB_USER -d $DB  < test.sql 2>&1 >/dev/null  | grep -q "service not known"
    RESULT=$?   # grep will return 0 if it finds 'failure',  non-zero if it didn't 
    if [ $RESULT -eq 0 ]; then
      echo "DB User $DB_USER can't connect to BI platform database [$DB] at $BIDBHOST Port $BIDBPORT -  Unknown Error"
      return 1
    fi

  fi


  return 0
}

#Before install verify can connect to all databases
#check_db_connect localhost 5432 truviso "" cqdb
#check_db_connect localhost 5432 tvconnectuser tvconnectuser@cisco tvdb
#
# Local Test
#

DB_NAME=cqdb

while true; do
    get_db_params
    check_db_connect $DB_NAME
    RESULT=$? 
    if [ $RESULT -ne 0 ]; then
        echo "Press enter to continue"
        read dummy
        continue
    fi
    break
done

#Now update sysconfig
pushd $SYSCONFIG  > /dev/null
sed '$a\
TRULINK_APP='$TRUVISO_HOME'/app \
PGPORT='$TRUVISO_PORT' \
PGHOST='$TRUVISO_IP' \
PA_HOME='$PA_HOME' \
PGDATA='$PGDATA' \
BIDBHOST='$BIDBHOST' \
BIDBPORT='$BIDBPORT' \
ANT_HOME='$PA_HOME/thirdparty/apache-ant-1.7.1' \
JAVA_HOME='$PA_HOME/thirdparty/$JDK' \
HA='$HA' \
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



echo "DB Connect Success"
##return 0



