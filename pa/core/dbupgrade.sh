#!/bin/sh
 
source ./common_env.sh
source ./common.sh
source ./utils.sh

#export LOG_FILE="/tmp/pa_install.log"
#export VERSION=`cat version`
#export DATE_TIME=`date +%Y%m%d_%s_%N`
#export TO="tee -a  ${LOG_FILE}"
export INSTALL_DIR_CORE=`echo $PWD`

#SYSCONFIG_FULLPATH=/etc/sysconfig/primeanalytics/primea


BU_DIR=/tmp/pa-bu1_1-conf_13c
source $SYSCONFIG_FULLPATH



function install_truviso() {
#    if [[ ! $LINUX_RELEASE =~ $RHEL6 ]]; then
#export TRUVISO_RPM=$TRUVISO_RPM5
#    fi

    chmod +x ./$TRUVISO_RPM
    ./$TRUVISO_RPM
    rpm -ihv --prefix=$PA_HOME/truviso  *.rpm
    RC=$?
    if [ $RC -ne 0 ]; then
       echo  "Fatal error installing truviso RPM" | $TO
       exit 1
    fi
}

####    Start Execution    ####

echo "Starting Database Upgrade under $PA_HOME (this may take a few moments...)"  | $TO


if [ -e "$TRUVISO_HOME/TruCQ/bin/pg_ctl" ]; then
  chkconfig --del trucq
  echo "Remove trucq service"

  echo "Backup configuration files"  | $TO
  pushd $PGDATA  >/dev/null
  if [ $? -ne 0 ]; then
       echo  "Fatal error backing up configruation files" | $TO
       exit 1
  fi
  mkdir -p $BU_DIR
  cp -pf postgresql.conf pg_ident.conf pg_hba.conf postmaster.opts $BU_DIR
  cp -pf /etc/sysconfig/primeanalytics/primea  $BU_DIR
  popd  >/dev/null

else
   echo "trucq server not installed"  | $TO
   sleep 3
   exit 1
fi
# No Need 11/20/2013 ???  rm -f /etc/init.d/trucq
rm -rf $PGDATA


rpm -qa | grep PrimeAnalytics-TruCQ | xargs rpm -ev --noscripts
rpm -qa | grep PrimeAnalytics-OGR | xargs rpm -ev 
rpm -qa | grep PrimeAnalytics-TruBuilder | xargs rpm -ev 
rpm -qa | grep PrimeAnalytics-TruLink | xargs rpm -ev 
rpm -qa | grep PrimeAnalytics-TruView | xargs rpm -ev 
rpm -qa | grep PrimeAnalytics-common | xargs rpm -ev  2> /dev/null

cd $PA_ROOT  >/dev/null
#rm -f /var/.pa_version
#rm -rf primeanalytics
rm -rf /etc/sysconfig/primeanalytics


### TEMP
export TRUVISO_RPM=PrimeAnalytics-master-1.rh6.x86_64-rpm.bin



# Install Truviso RPM 1.1
echo "install truviso RPM"
pushd $INSTALL_DIR_CORE  >/dev/null
install_truviso
popd  >/dev/null

cp -pf $BU_DIR/primea /etc/sysconfig/primeanalytics


##   Restore DB from backup   ##
echo "Restore database from backup file"  | $TO
pushd $PA_HOME/bin/backup_restore/Database  >/dev/null
while true; do
  read -p "Enter full pathname of database backup file " ans
  if [ -f $ans ]; then
    python $INSTALL_DIR_CORE/sqlupgrade.py $ans ${ans}.upgrade
    su primea -c "./restore_db_repository.sh  ${ans}.upgrade"
    if [ $? -ne 1 ]; then
      break
    fi
  fi
  echo "Please retry"  | $TO
done
echo "Database restore completed"  | $TO

##  Restore configuration files and restart DB  ##
#      note that db restore doesn't start DB
#
echo "Restore configuration files"
pushd $BU_DIR  >/dev/null
cp -pf postgresql.conf pg_ident.conf pg_hba.conf postmaster.opts $PGDATA

#echo >> $PGDATA/postgresql.conf
#echo "#Set default as left edge align as upgrading from 1.0" >> $PGDATA/postgresql.conf
#echo "cq_default_right_edge_exclusive = false" >> $PGDATA/postgresql.conf

echo "Start DB Service"
service $DB_SERVICE_NAME start
STATUS=$?
if [ $STATUS -ne 0 ]; then
  err_exit "Fatal error can't start database after restoring configuration files", errno $STATUS
fi

echo "Database restore completed"  | $TO







