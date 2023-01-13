#!/bin/sh


#
# This version is called to permit PA to be installed in a HA configuration
#

export HA=true
export IR_HA=`pwd`/core/ha


#######################################
###  Start of execution
#######################################

usage() {
   echo "USAGE: $0 <prime analytics root> <all|db>"
   echo -e '\n\tall - All Components \n\tdb - Streams Database'
}




# For HA each component will be installed on a separate box
if [ $# -ne 2 ]; then
   usage
   exit 1
fi

export PA_ROOT=$1
export INSTALL_TYPE=$2

if [ "$INSTALL_TYPE" != "db" ] && [ "$INSTALL_TYPE" != "all" ]; then
   usage
   exit 1
fi

./primeanalytics.sh $PA_ROOT $INSTALL_TYPE

