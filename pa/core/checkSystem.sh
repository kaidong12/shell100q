#!/bin/sh


if [ -f "/etc/redhat-release" ]; then
    export LINUX_RELEASE_FILE="/etc/redhat-release"
else
    export LINUX_RELEASE_FILE="/etc/*-release"
fi
LINUX_RELEASE=`cat ${LINUX_RELEASE_FILE}`
RH5="Red Hat.* Linux.*5\..*"
RH6="Red Hat.* Linux.*6\.4.*"

MDISK=4
AVAIL=`df -Ph $PA_ROOT | tail -1 | awk '{print $4}'`

### Memory ###
MIN_TOTALMEM=8
MIN_FREEMEM=2
MIN_FREESWAP=6
MEG=1048576
#use this value for rounding
MEG=1000000
TOTALMEM=$(grep MemTotal /proc/meminfo | awk '{print $2}')
FREEMEM=$(grep MemFree /proc/meminfo | awk '{print $2}')
FREESWAP=$(grep SwapFree /proc/meminfo | awk '{print $2}')


### Shared Memory ###
# shmmax(maximum size in bytes of a single shared memory segment ) 
MIN_SHMMAX=4118597632
SHMMAX=$(cat /proc/sys/kernel/shmmax)
# shmmni(number of shared memory segments) 
MIN_SHMMNI=4096
SHMMNI=$(cat /proc/sys/kernel/shmmni)
# shmall(total amount of shared memory pages that can be used system wide)
MIN_SHMALL=1508275
SHMALL=$(cat /proc/sys/kernel/shmall)

#echo "SM: $SHMMAX  $SHMMNI   $SHMALL"

checkFailed() {
  while true; do
    echo $1
    read -p "Do you want to exit install? (yes or no) " yn
      case $yn in
          yes ) return 1;;
          no ) return 0;;
          * ) echo "Please answer yes or no.";;
      esac
  done
}




#Check OS
if [[ ! $LINUX_RELEASE =~ $RH6 ]];  
then
   checkFailed "Prime Analytics is only certified on RHEL 6.4 and you are attempting to install on $LINUX_RELEASE. Cisco will not support this installation and it is recommended you exit."
   if [ $? = 1 ]; then
      exit 1
   fi
fi


#Check disk space of specified folder(values are in GB)
file=$AVAIL
x=`echo "${file//[^0-9]*/}"`
y=`echo "${file/*[^A-Z]/}"`

if [ $y = 'G' ];then
   if [[ $x -lt $MDISK ]]; then
      checkFailed "Not enough disk space on $PA_ROOT. Available: $AVAIL, Required: ${MDISK}G. Cisco will not support this installation and it is recommended you exit."
      if [ $? = 1 ]; then
         exit 1
      fi
   fi
elif [ $y != 'T' ];then
   checkFailed "Not enough disk space on $PA_ROOT. Available: $AVAIL, Required: ${MDISK}G. Cisco will not support this installation and it is recommended you exit."
   exit 0
fi

#Check shared memory
if [[ $SHMMAX  -lt $MIN_SHMMAX ]]; then
   checkFailed "Shared Memory Parameter SHMMAX is not large enough. Current: $SHMMAX bytes, Minimum Required: $MIN_SHMMAX bytes. Cisco will not support this installation and it is recommended you exit."
   if [ $? = 1 ]; then
      exit 1
   fi
fi

if [[ $SHMMNI  -lt $MIN_SHMMNI ]]; then
   checkFailed "Shared Memory Parameter SHMMNI is not large enough. Current: $SHMMNI segments, Minimum Required: $MIN_SHMMNI segments. Cisco will not support this installation and it is recommended you exit."
   if [ $? = 1 ]; then
      exit 1
   fi
fi

if [[ $SHMALL  -lt $MIN_SHMALL ]]; then
   checkFailed "Shared Memory Parameter SHMALL is not large enough. Current: $SHMALL pages, Minimum Required: $MIN_SHMALL pages. Cisco will not support this installation and it is recommended you exit."
   if [ $? = 1 ]; then
      exit 1
   fi
fi

#Check Memory
T=`expr $TOTALMEM / $MEG`
if [[ $T  -lt $MIN_TOTALMEM ]]; then
   checkFailed "Not enough total memory. Available GB: $T, Minimum Required: $MIN_TOTALMEM. Cisco will not support this installation and it is recommended you exit."
   if [ $? = 1 ]; then
      exit 1
   fi
fi

T=`expr $FREEMEM / $MEG`
if [[ $T  -lt $MIN_FREEMEM ]]; then
   checkFailed "Not enough free memory. Available GB: $T, Minimum Required: $MIN_FREEMEM. Cisco will not support this installation and it is recommended you exit."
   if [ $? = 1 ]; then
      exit 1
   fi
fi

T=`expr $FREESWAP / $MEG`
if [[ $T  -lt $MIN_FREESWAP ]]; then
   checkFailed "Less than recommended amount of free swap space. Available GB: $T, Minimum Recommended: $MIN_FREESWAP. Cisco will not support this installation and it is recommended you exit."
   if [ $? = 1 ]; then
      exit 1
   fi
fi

exit 0





