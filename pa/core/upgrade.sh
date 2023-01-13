#!/bin/sh

######################################################################
# Main script for upgrade
######################################################################

#### cd core >/dev/null

source ./common_env.sh
source ./common.sh
source ./utils.sh

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
export LINUX_RELEASE_FILE="/etc/*-release"
export LINUX_RELEASE=`cat ${LINUX_RELEASE_FILE}`
export TRUVISO_RPM=PrimeAnalytics-master-1.rh6.x86_64-rpm.bin
export TRUVISO_RPM5=PrimeAnalytics-master-1.rh5.x86_64-rpm.bin
export RHEL6="Red Hat.* Linux.*6\..*"

#Upgrade
export CUR_VERSION="1.0"
export UP_VERSION="1.1"




function upgrade_truviso() {
    echo "Upgrade Database" | $TO
    ./dbupgrade.sh
    if [ $? -ne 0 ]; then
	err_exit "Database upgrade failed"
    fi
}


function upgrade_3p() {
    echo "Upgrade third party components" | $TO
    tar -C $PA_HOME/thirdparty -zxvf protobuf-2.5.0.tar.gz  >/dev/null
    if [ $? -ne 0 ]; then
        err_exit "Fatal error installing protobuf"
    fi

#uninstall Java 6 and replace with Java 7
    pushd $PA_HOME/thirdparty >/dev/null
    rm -rf jdk1.6.0_37
    if [ $? -ne 0 ]; then
        err_exit "Fatal error uninstalling Java 6"
    fi
    popd >/dev/null
    tar -C $PA_HOME/thirdparty -zxvf jdk-7u45-linux-x64.tar.gz  >/dev/null
    if [ $? -ne 0 ]; then
        err_exit "Fatal error installing Java 7"
    fi
    sed s/jdk1\.6\.0_37/jdk1.7.0_45/g <$SYSCONFIG_FULLPATH  >/tmp/c-1-2.tmp.pcfg
    cp -f /tmp/c-1-2.tmp.pcfg $SYSCONFIG_FULLPATH
    if [ $? -ne 0 ]; then
        err_exit "Fatal error updating Java 7 path"
    fi
    export PATH=$PA_HOME/thirdparty/$JDK/bin:$PATH
}  



function upgrade_biplatform() {

   echo "Upgrade BI Platform" | $TO

   ./bipbackup.sh
   pushd ../pentaho  > /dev/null
   chmod a+x bi_pwd_update.sh
   chmod a+x upgrade_bi_platform.sh
   su bipuser -c "./upgrade_bi_platform.sh"
    popd  >/dev/null
}


upgrade_bin() {
    cp appupgrade.sh $PA_HOME/bin
    pushd $PA_HOME/bin/backup_restore  >/dev/null
    chmod u+x BIPlatform/*.sh
    chown -R bipuser BIPlatform

    cp -f $INSTALL_DIR_CORE/../pentaho/bi_pwd_update.sh ../

    chmod u+x Database/*.sh
    chown -R primea Database
    popd  >/dev/null
}


upgrade_app() {
   pushd $PA_HOME/bin  >/dev/null
   echo "Upgrade Sample Applications" | $TO
   ./appupgrade.sh $PA_HOME/biplatform/sampledatagenerator
   popd  >/dev/null
}




#############################################################
###            Start of execution
#############################################################

rm -f $LOG_FILE
DATE=`date`
echo "Start upgrade on $UHOST $DATE " | $TO


if [ ! -f "/etc/sysconfig/primeanalytics/primea" ]; then
   err_exit "Valid 1.0 installation doesn't exist: Prime Analytics sysconfig not found"
fi

source $SYSCONFIG_FULLPATH

cat /var/.pa_version | grep "1\.0" >/dev/null
if [ $? -ne 0 ]; then
   err_exit "Can only upgrade from 1.0 to 1.1. Current installed version is not 1.0"
fi


service biplatform  status >/dev/null
if [ $? -eq 1 ]; then
    err_exit "Can only upgrade single node installation. Can't find BIPlatform or dependent library"
fi

service trucq status >/dev/null
if [ $? -eq 1 ]; then
   err_exit "Can only upgrade single node installation. Can not find trucq or dependent library"
fi

## preconditions met to start upgrade ##
echo "Warning: You should do a full backup before starting the upgrade"
  while true; do
    echo $1
    read -p "Do you want to exit upgrade? (yes or no) " yn
      case $yn in
          yes ) exit  1;;
          no ) break;;
          * ) echo "Please answer yes or no.";;
      esac
  done





service biplatform stop
service trucq stop

upgrade_3p

upgrade_truviso

cd $INSTALL_DIR_CORE  > /dev/null

source $SYSCONFIG_FULLPATH
export JAVA_HOME="$PA_HOME/thirdparty/$JDK"
echo -e  "source /etc/sysconfig//primeanalytics/primea\nexport PATH=$JAVA_HOME/bin:$PATH\nsource $PA_HOME/bin/pa_env.sh" >> ~bipuser/.bash_profile
chmod a+w $LOG_FILE
export CQENGINE=$CQENGINE
export BIDBPORT=$BIDBPORT
export BIDBHOST=$BIDBHOST
upgrade_biplatform

upgrade_bin

upgrade_app


 


### Wrap-up ###
cd $PA_HOME
cd install_log  >/dev/null
mv pa_install.log pa_install.log-1_0
cp /tmp/pa_install.log install_log
cp $INSTALL_DIR_CORE/version $PA_HOME
cd $PA_HOME  >/dev/null
mv version /var/.pa_version
 
echo "Upgrade Successfully Completed `date`" | $TO

####################    END UPGRADE ##########################

