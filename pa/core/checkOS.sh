#!/bin/sh

LINUX_RELEASE_FILE="/etc/*-release"

LINUX_RELEASE=`cat ${LINUX_RELEASE_FILE}`
RH5="Red Hat.* Linux.*5\..*"
RH6="Red Hat.* Linux.*6\..*"

if [[ $LINUX_RELEASE =~ $RH5 || $LINUX_RELEASE =~ $RH6 ]];  
then
   exit 0
else
   exit 1
fi



