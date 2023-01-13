#!/bin/sh

#rpm -qa 
#rpm -ev 
 
CORRUPT=N
export LINUX_RELEASE_FILE="/etc/*-release"
export LINUX_RELEASE=`cat ${LINUX_RELEASE_FILE}`
export RHEL6="Red Hat.* Linux.*6\..*"

#Best effort to cleanup a corrupted install
clean() {
  echo "Attempting best effort cleanup"
  rm -f /var/.pa_version 2> /dev/null
  rm -rf $PA_ROOT/primeanalytics 2> /dev/null
  echo "Cleanup attempt completed. Please contact customer support if you still have install problems"
}


if [ $# -ne 1 ]; then
   echo "USAGE: $0 <prime analytics root>"
   exit 1
fi
PA_ROOT=$1

if [ ! -e $PA_ROOT/primeanalytics ]; then
   echo  "Prime Analytics not installed under $PA_ROOT"
   exit 1
fi
if [ ! -f "/etc/sysconfig/primeanalytics/primea" ]; then
   echo "Prime Analytics sysconfig not found"
   CORRUPT=Y
fi
if [ "$CORRUPT" = "Y" ]; then
  echo "Warning, this may be a corrupted installation"
  while true; do
    read -p "Do you want to attempt a cleanup? (yes or no) " yn
      case $yn in
          yes ) clean
                exit 1;;
          no )  exit 1;;
          * ) echo "Please answer yes or no.";;
      esac
  done
fi

 
SYSCONFIG_FULLPATH=/etc/sysconfig/primeanalytics/primea
source $SYSCONFIG_FULLPATH
echo "Starting uninstall $PA_HOME (this may take a few moments...)"

if [ -d "$PA_ROOT/primeanalytics/biplatform/server/biserver-ee" ]; then
   echo "Uninstalling BI Platform"
   service biplatform stop
   chkconfig --del biplatform
   SOLUTION_FOLDER=$(su - bipuser -c "env"|grep PA_PENTAHO_SOLUTIONS|cut -d "=" -f2)	
   if [ -d "$SOLUTION_FOLDER" ]; then
    echo "Deleting Solution Folder at $SOLUTION_FOLDER"
    rm -Rf $SOLUTION_FOLDER
   fi

   userdel -f -r  bipuser
   groupdel bipgroup
   rm /etc/init.d/biplatform
#   $CQENGINE/psql -h $PGHOST -p $PGPORT -U $CQUSER < clean_bip_db.sql
else
   echo "BI Platform not installed"
fi

# Fix for CSCui31902
echo "Stopping all TruLink processes"
ps -aef |grep TruLink|grep -v ps | awk '{ print $2 }' | xargs kill $i 2>&1 >/dev/null
sleep 5

if [ -e "$TRUVISO_HOME/TruCQ/bin/pg_ctl" ]; then
  echo "Uninstall TruCQ"
  echo "Stopping TruCQ"
  service trucq stop
  sleep 10
  chkconfig --del trucq
  sleep 5
  echo "Remove service"
else
   echo "trucq server not installed"
   sleep 3
fi
rm -f /etc/init.d/trucq
rm -rf $PGDATA
if [ -n "${BIDBPGDATA+x}" ]; then
  echo "Uninstall BI HA TruCQ"
  echo "Stopping BI HA TruCQ"
  service bitrucq stop
  sleep 10
  chkconfig --del bitrucq
  sleep 5
  echo "Remove service"
  rm -f /etc/init.d/bitrucq
  rm -rf $BIDBPGDATA
fi

#
# Try to remove TruBuilder/TruView/OGR still, the script may run against
# old version who contains those components.
#
rpm -qa | grep PrimeAnalytics-TruCQ | xargs rpm -ev --noscripts
rpm -qa | grep PrimeAnalytics-OGR | xargs rpm -ev 2> /dev/null
rpm -qa | grep PrimeAnalytics-TruBuilder | xargs rpm -ev  2> /dev/null
rpm -qa | grep PrimeAnalytics-TruLink | xargs rpm -ev 
rpm -qa | grep PrimeAnalytics-TruView | xargs rpm -ev 2> /dev/null
rpm -qa | grep PrimeAnalytics-common | xargs rpm -ev  2> /dev/null

cd $PA_ROOT
rm -f /var/.pa_version
rm -rf primeanalytics
rm -rf /etc/sysconfig/primeanalytics
#
# failed install can leave junk so we unconditionally cleanup here
#

userdel -f -r  primea 2> /dev/null
userdel -f -r  bipuser 2> /dev/null
groupdel bipgroup 2> /dev/null
echo "Uninstall completed"
