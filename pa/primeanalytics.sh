#!/bin/sh


######################################################################
# Main script for master installer
######################################################################

cd core

source ./common_env.sh
source ./common.sh
source ./utils.sh
if [ "$HA" = "true" ]; then
  source ha/hautils.sh
fi



export TRUVISO_IP="localhost"
export DB_USER=$PA_USER
export DB_PASSWORD=""
export BIDBPORT=5432
export BIDBHOST=localhost
export UHOST=`uname -n`
export INSTALL_DIR_CORE=`echo $PWD`
export LOG_FILE="/tmp/pa_install.log"
export VERSION=`cat version`
export DATE_TIME=`date +%Y%m%d_%s_%N`
export TO="tee -a  ${LOG_FILE}"
if [ -f "/etc/redhat-release" ]; then
    export LINUX_RELEASE_FILE="/etc/redhat-release"
else
    export LINUX_RELEASE_FILE="/etc/*-release"
fi
export LINUX_RELEASE=`cat ${LINUX_RELEASE_FILE}`
export TRUVISO_RPM=PrimeAnalytics-master-1.rh6.x86_64-rpm.bin
export TRUVISO_RPM5=PrimeAnalytics-master-1.rh5.x86_64-rpm.bin
export RHEL6="Red Hat.* Linux.*6\..*"

rm -f $LOG_FILE




function install_truviso() {
    if [[ ! $LINUX_RELEASE =~ $RHEL6 ]]; then
        export TRUVISO_RPM=$TRUVISO_RPM5
        err_exit "RHEL5 not supported yet"
    fi
    chmod +x ./$TRUVISO_RPM
    ./$TRUVISO_RPM
    rpm -ihv --prefix=$PA_HOME/truviso  *.rpm
    RC=$?
    if [ $RC -ne 0 ]; then
       err_exit "Fatal error installing truviso RPM"
    fi


    if [ "$IDB_SERVER" = "true" ]
    then
        echo "Setup Server DB" | $TO
        ./configDB.sh 
        if [ $? -ne 0 ]; then
           exit 1
        fi
    #Call sql file in the same way as other samples
   #     ./createUCTables.sh
        
    fi
    if [ "$IDB_BIHA" = "true" ]; then
        echo "Setup Server DB for BI HA" | $TO
        ./configDB-BIHA.sh
        if [ $? -ne 0 ]; then
           exit 1
        fi
    fi

#check if client only install
    if [ "$IDB_BIHA" = "false" ] && [ "$IDB_SERVER" = "false" ]; then
        if [ "$IBIP" = "true" ];  then
            echo "Setup Client DB Configuration for BI Platform" | $TO
            source ./configDB4Client.sh
            if [ $? -ne 0 ]; then
              err_exit "Fatal error, can't connect to remote TruCQ instance"
            fi
        fi
       ./configDBClient.sh
    fi


#sysconfig file is part of Truviso RPM and not fully set until now, so need to get env vars here
source $SYSCONFIG_FULLPATH

}


function install_3p() {
    echo "Install third party components" | $TO
    mkdir $PA_HOME/thirdparty
    tar -C $PA_HOME/thirdparty -zxvf apache-ant-1.7.1-bin.tar.gz >/dev/null
        if [ $? -ne 0 ]; then
        err_exit "Fatal error installing Ant"
    fi
    tar -C $PA_HOME/thirdparty -zxvf protobuf-2.5.0.tar.gz  >/dev/null
    tar -C $PA_HOME/thirdparty -zxvf jdk-7u45-linux-x64.tar.gz  >/dev/null
    if [ $? -ne 0 ]; then
        err_exit "Fatal error installing Java"
    fi
    export PATH=$PA_HOME/thirdparty/$JDK/bin:$PATH
}  

install_bin() {
    cp -rf bin $PA_HOME
    tar -C $PA_HOME/bin/backup_restore -zxvf $INSTALL_DIR_CORE/../pentaho/backup_restore-*.tar.gz >/dev/null
    pushd $PA_HOME/bin/backup_restore  >/dev/null
    if [ "$INSTALL_TYPE" = "all" ] || [ "$INSTALL_TYPE" = "bip" ]; then
        chmod u+x BIPlatform/*.sh
        chown -R bipuser BIPlatform
        cp -f $INSTALL_DIR_CORE/../pentaho/bi_pwd_update.sh ../
        cp -f $INSTALL_DIR_CORE/../pentaho/bip-change-password.jar ../
    fi
    if [ "$INSTALL_TYPE" = "all" ] || [ "$INSTALL_TYPE" = "db" ]; then
        chmod u+x Database/*.sh
        chown -R primea Database
    fi
    popd  >/dev/null
}

function install_biplatform() {

   echo "Install BI Platform" | $TO
   pushd ../pentaho  > /dev/null
   pushd SQL  > /dev/null

# replace default IP and Port as needed
   ../../core/configBISQL.sh

   if [ $? -ne 0 ]; then
       err_exit "Fatal error unexpected calling configBISQL.sh"
   fi

   echo "Current PATH is $PATH"  | $TO
#   CONNECT_STRING="-h $TRUVISO_IP -p $PGPORT -U $DB_USER"
   TRUCQ_CONNECT_STRING="-h $TRUVISO_IP -p $PGPORT -U $DB_USER"
   BIDB_CONNECT_STRING="-h $BIDBHOST -p $BIDBPORT -U $DB_USER"
   HIBERNATE_CONNECT_STRING="-h $BIDBHOST -p $BIDBPORT -U hibuser"

   echo "DB parameters for BI Platform:  psql $BIDB_CONNECT_STRING" | $TO
   echo "DB parameters for TruCQ:  psql $TRUCQ_CONNECT_STRING" | $TO
   echo "DB parameters for Hibernate:  psql $HIBERNATE_CONNECT_STRING" | $TO

# If only install bip then check if remote DB already setup. This should only happen for restore and possibly future upgrade
# If all option then always do fresh DB setup
     INIT_TV=0
     INIT_BIDB=0
     if [ "$BIP_ONLY" = "true" ]; then 
       check_dbreset tvdb $TRUVISO_IP $PGPORT $DB_USER "tvdb already exists on $TRUVISO_IP. Overwrite" 
       INIT_TV=$?
       check_dbreset hibernate $BIDBHOST $BIDBPORT $DB_USER "BI Platform database already exists on $BIDBHOST. Overwrite" 
       INIT_BIDB=$?
     fi
     if [ $INIT_TV = 0 ]; then
       psql  $TRUCQ_CONNECT_STRING < mkschema.sql >>$LOG_FILE 2>&1
       if [ $? -ne 0 ]; then
           err_exit "Fatal error executing mkschema.sql"
       fi

       psql  $TRUCQ_CONNECT_STRING < ddl_dml_sample_netflow_csv.sql >>$LOG_FILE 2>&1
       if [ $? -ne 0 ]; then
           err_exit "Fatal error creating NetFlow CSV"
       fi


       psql  $TRUCQ_CONNECT_STRING < ddl_dml_syslog_analytics.sql >>$LOG_FILE 2>&1
       if [ $? -ne 0 ]; then
           err_exit "Fatal error creating syslog sample data source"
       fi

  psql  $TRUCQ_CONNECT_STRING < ../../core/usagecollection.sql >>$LOG_FILE 2>&1
      if [ $? -ne 0 ]; then
      err_exit "Fatal error executing UsageCollection.sql"
      fi
echo "Create database for UsageCollection completed."

       
# Edr sample requires hstore
       psql  $TRUCQ_CONNECT_STRING < $PA_HOME/truviso/TruCQ/share/postgresql/contrib/hstore.sql >>$LOG_FILE 2>&1
       if [ $? -ne 0 ]; then
        err_exit "Fatal error installing HSTORE"
       else
        echo "HSTORE installed"
       fi


       psql $TRUCQ_CONNECT_STRING < ddl_dml_edr_analytics.sql >>$LOG_FILE 2>&1
       if [ $? -ne 0 ]; then
        err_exit "Fatal error creating Edr Analytics"
       fi

       
     fi


     if [ $INIT_BIDB = 0 ]; then
       psql  $BIDB_CONNECT_STRING < create_repository_postgresql.sql >>$LOG_FILE 2>&1
       if [ $? -ne 0 ]; then
           err_exit "Fatal error creating Pentaho repository"
       fi
#
# note hibuser is created here
#      pg_restore -C -d cqdb -i --format=c $BIDB_CONNECT_STRING  hibernate.dmp 
#       if [ $? -ne 0 ]; then
#           err_exit "Fatal error restoring hibernate"
#       fi

#
#       psql  $HIBERNATE_CONNECT_STRING < update_hibernate.sql >>$LOG_FILE 2>&1
#       if [ $? -ne 0 ]; then
#           err_exit "Fatal error update_hibernate.sql"
#       fi

#       psql  $HIBERNATE_CONNECT_STRING < create_conn_bisample.sql >> $LOG_FILE 2>&1
#       psql  $HIBERNATE_CONNECT_STRING < create_conn_edr.sql >> $LOG_FILE 2>&1
    
    
 #JCR for Pentaho 5 created here
      psql  $BIDB_CONNECT_STRING <create_jcr_postgresql.sql  >> $LOG_FILE 2>&1
      if [ $? -ne 0 ]; then
           err_exit "Fatal error creating jackrabbit jcr_user user"
       fi

    #  jackrabbit is restored here
      pg_restore -C -d cqdb -i --format=c $BIDB_CONNECT_STRING  jackrabbit.dmp 
       if [ $? -ne 0 ]; then
        err_exit "Fatal error restoring jackrabbit db"
    fi
    
       psql  $BIDB_CONNECT_STRING < create_quartz_postgresql.sql >>$LOG_FILE 2>&1
       if [ $? -ne 0 ]; then
           err_exit "Fatal error creating Pentaho quartz"
       fi

       psql  $BIDB_CONNECT_STRING < create_tvdb.sql >>$LOG_FILE 2>&1
       if [ $? -ne 0 ]; then
           err_exit "Fatal error creating TVDB"
       fi

       pg_restore -C -d cqdb -i --format=c  $BIDB_CONNECT_STRING  tvdb.dmp 
       if [ $? -ne 0 ]; then
           err_exit "Fatal error restoring TV"
       fi

       psql  $BIDB_CONNECT_STRING < update_tvdb.sql >>$LOG_FILE 2>&1
       if [ $? -ne 0 ]; then
           err_exit "Fatal error updating TVDB"
       fi
       
       psql  $BIDB_CONNECT_STRING < update_edr_tvdb.sql >>$LOG_FILE 2>&1
       if [ $? -ne 0 ]; then
           err_exit "Fatal error updating EDR TVDB"
       fi
       
     fi

#   can't do both live and local file at this time
#   psql $CONNECT_STRING < ddl_dml_sample_netflow.sql 
#   if [ $? -ne 0 ]; then
#       err_exit "Fatal error creating NetFlow live sample data source"
#   fi

    popd  > /dev/null



###<BASE_PATH> <TRUVISO_METADATA_TABLE_MACHINE_IPADDRESS> <TRUVISO_METADATA_TABLE_MACHINE_PORT> <TV_IPADDRESS> <TV_PORT>
   chmod a+x BI_Platform.sh
   chmod a+x bi_pwd_update.sh
   echo "Call ./BI_Platform.sh $PA_ROOT $BIDBHOST $BIDBPORT $TRUVISO_IP $PGPORT" | $TO
chmod a+w $PA_HOME
groupadd bipgroup
while true; do
    useradd -p A1fYkP68q5MEY -G bipgroup bipuser 2> /dev/null
    ERR=$?
    if [ $ERR -ne 0 ]; then
        echo  "Can't create BI Platform user bipuser(Error $ERR). Please delete bipuser and try again" 
        read -p "Press Enter to continue" dummy
    else
        break;
    fi
done
echo -e  "source /etc/sysconfig//primeanalytics/primea\nexport PATH=$JAVA_HOME/bin:$PATH\nsource $PA_HOME/bin/pa_env.sh" >> ~bipuser/.bash_profile
#su bipuser -c "./BI_Platform.sh $PA_ROOT $BIDBHOST $BIDBPORT $TRUVISO_IP $PGPORT"
./BI_Platform.sh ${PA_ROOT} ${BIDBHOST} ${BIDBPORT} ${TRUVISO_IP} ${PGPORT}
if [ $? -ne 0 ]; then
  err_exit "Fatal error: Could not install BI Platform" 
fi
popd
chmod go-w $PA_HOME 
cp -f biplatform /etc/init.d
if [ $? -ne 0 ]; then
   echo "Warning: can't create biplatform service" | $TO
fi
chkconfig --add biplatform
chkconfig biplatform on
}


########################################################
###            Start of execution
########################################################


#./checkOS.sh
#if [ $? -ne 0 ]; then
  #err_exit "Fatal error: Unsupported operating system version - $LINUX_RELEASE"
  #exit -1
#fi



if [ $# -ne 2 ]; then
   echo "USAGE: $0 <prime analytics root> <all|db|bip>"
   exit 1
fi
export INSTALL_TYPE=$2
if [ "$INSTALL_TYPE" != "all" ] && [ "$INSTALL_TYPE" != "db" ] && [ "$INSTALL_TYPE" != "bip" ] && ( [ "$INSTALL_TYPE" != "tl" ] || [ "$HA" != "true" ] ) &&  [ "$HA" != "true" ]; then
   err_exit "USAGE: Valid install types are:  <all|db|bip>"
   exit 1
fi

#Get install directory
CUR_DIR=`pwd`

cd ..

#Readlink will result in an absolute path if relative given.
ABSOLUTE_PATH=$(readlink -f $1)

echo $ABSOLUTE_PATH

cd $CUR_DIR

if [ ! -d "$ABSOLUTE_PATH" ]; then
   err_exit "Specified root directory $ABSOLUTE_PATH doesn't exist"
fi  
export PA_ROOT=$ABSOLUTE_PATH



#check license acceptance
./checkLicense.sh
if [ $? -ne 0 ]; then
  exit -1
fi

#check permissions
echo "Checking directory permissions" | $TO
useradd prime1te24st2a 2> /dev/null
su prime1te24st2a -c "ls ../pentaho" &> /dev/null
if [ $? -ne 0 ]; then
  userdel -rf  prime1te24st2a > /dev/null
  err_exit "Fatal error: user primea doesn't have permissions to complete install in current directory $PWD"
fi
su prime1te24st2a -c "ls $PA_ROOT" &> /dev/null
if [ $? -ne 0 ]; then
  userdel -rf  prime1te24st2a > /dev/null
  err_exit "Fatal error: user primea doesn't have permissions to complete install in specified directory $PA_ROOT"
fi
userdel -rf  prime1te24st2a > /dev/null

sync; echo 3 > /proc/sys/vm/drop_caches 
./checkSystem.sh
RC=$?
if [ $RC -ne 0 ]; then
  exit -1
fi


#check disk space of specified folder(values are in GB)
#MDISK=4
#MDISK=2
#AVAIL=`df -Ph $PA_ROOT | tail -1 | awk '{print $4}'`
#file=$AVAIL
#x=`echo "${file//[^0-9]*/}"`
#if [[ $x -lt $MDISK ]]; then
#  err_exit "Not enough space on $PA_ROOT. Available: $AVAIL, Required: ${MDISK}G"
#fi


export PA_HOME="$PA_ROOT/primeanalytics"
export JAVA_HOME="$PA_HOME/thirdparty/$JDK"
export ANT_HOME="$PA_HOME/thirdparty/apache-ant-1.7.1"
export TRUVISO="$PA_HOME/truviso"
export BIPLATFORM="$PA_HOME/biplatform"
export TRUVISO_HOME=$PA_HOME/truviso
export PATH="$TRUVISO_HOME/TruCQ/bin:$JAVA_HOME/bin:$ANT_HOME/bin:$PATH"

#check if for HA Configuration
if [ "$HA" != "true" ]; then
   export HA=false
fi


# Check if PA Home directory exists
if [ -e "$PA_HOME" ]
then
  err_exit "Prime Analytics is already installed at $PA_HOME" 
else
  if [ -e "$SYSCONFIG" ]; then
      err_exit "Detected prior version of Prime Analytics. Please run uninstall and then retry"
  fi
  if [ -e "/var/.pa_version" ]; then
      err_exit "Detected prior version of Prime Analytics. Please run uninstall and then retry"
  fi
  if [ -e "$VER" ]; then
      err_exit "Detected prior version of Prime Analytics. Please run uninstall and then retry"
  fi
  mkdir -p $PA_HOME
  if [ $? -ne 0 ]; then
        err_exit "Fatal error creating $PA_HOME"
        echo "why Here ceate PA home"
        exit -1
  fi
fi






## START ----------

if [ "$HA" = "true" ]; then
  get_service_dir
fi



## END-------

mkdir $PA_HOME/uninstall
cp $INSTALL_DIR_CORE/uninstall.sh $PA_HOME/uninstall
cp -f validateutils.jar /tmp

DATE=`date`
echo "Start install on $UHOST $DATE " | $TO
echo "Install options,  Type: $INSTALL_TYPE, HA: $HA, Root: $PA_ROOT" | $TO
echo "Version: $VERSION" | $TO
echo "OS: $LINUX_RELEASE" | $TO

#Install 3rd party applications
install_3p

# Figure out what to install
if [ "$INSTALL_TYPE" = "db" ] ||  [ "$INSTALL_TYPE" = "all" ]; then
  echo "Install Truviso Server" | $TO
  DB_SERVER="true"
else
  echo "Install Truviso Client" | $TO
  DB_SERVER="false"
fi


export IDB_SERVER="false" 
export IDB_BIHA="false"  
export IBIP="false"
export ITL="false"
export BIP_ONLY="false"
if [ "$HA" = "true" ]; then
 case $INSTALL_TYPE in
          all ) export IDB_SERVER="true"
                export IDB_BIHA="true"
                export IBIP="true";;

          bip ) export IBIP="true"
                export BIP_ONLY="true";;

          db ) export IDB_SERVER="true";;

          bidb ) export IDB_BIHA="true";;

          tl ) export ITL="true";;

 esac
else
 case $INSTALL_TYPE in
          all ) export IDB_SERVER="true"
                export IBIP="true";;

          bip ) export BIP_ONLY="true" 
                export IBIP="true";;

          db ) export IDB_SERVER="true";;

          tl ) export ITL="true";;

 esac

fi


#Install Truviso
install_truviso 



#Check if Install BI Platform
if [ "$IBIP" = "true" ]; then
   install_biplatform
   ./configBISA.sh
fi


#install bin utils
install_bin


# Wrapup
cd $PA_HOME
#mkdir uninstall
#cp $INSTALL_DIR_CORE/uninstall.sh uninstall
mkdir install_log
cp /tmp/pa_install.log install_log
cp $INSTALL_DIR_CORE/version $PA_HOME
cd $PA_HOME
mv version /var/.pa_version
sync; echo 3 > /proc/sys/vm/drop_caches
echo "DB Host: $TRUVISO_IP, DB Port: $PGPORT, DB User: $DB_USER" | $TO
echo "Install Successfully Completed `date`" | $TO

