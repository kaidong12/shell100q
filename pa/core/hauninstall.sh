#!/bin/sh

if [ $# -ne 1 ]; then
   echo "USAGE: $0 <prime analytics root>"
   exit 1
fi
PA_ROOT=$1

if [ ! -e $PA_ROOT/primeanalytics ]; then
   echo  "Prime Analytics not installed under $PA_ROOT"
   exit 1
fi


if [ -e "/etc/sysconfig/primeanalytics/primea" ]; then
   . /etc/sysconfig/primeanalytics/primea
  if [ -e "$PA_HOME/bin/ha-env" ]; then
    source $PA_HOME/bin/ha-env
    echo "Stopping HA services (this may take a few moments)"
    ccs -h `uname -n`  --stopall
  else
    if [ ! "HA" = "true" ]; then
      echo "This is not a HA installation"
      exit 1
    fi
  fi
fi
./uninstall.sh $1
if [ -e "$DBDIRA" ]; then
  rm -rf $DBDIRA/*
fi
if [ -e "$DBDIRB" ]; then
  rm -rf $DBDIRB/*
fi
if [ -e "$SVCDIR" ]; then
  rm -rf $SVCDIR/*
fi
# for HostB cleanup
userdel -rf $CQUSER 2> /dev/null

