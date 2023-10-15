#!/bin/sh
# Upgrade the TruLink 1.0 applications and projects to 1.1

# Prepare the environments
if [ "" = "$PA_HOME" ] ; then

   source /etc/sysconfig/primeanalytics/primea
fi

# Version check

LOG4J=$PA_HOME/truviso/TruLink/template/customizations/templates/log4j.properties
BUILD=$PA_HOME/truviso/TruLink/template/build.xml

if [ ! -f $LOG4J -o ! -f $BUILD ] ; then
    echo "Incomplete installation: please make sure the TruLink installation is already finished before application upgrade."
    exit
fi

if [ $# -eq 1 ]; then
   APP_DIR=$1
else
  while true; do
    read -p "Enter application root directory:" ans
    if [ "$ans" = "" ]
    then
        break
    fi
    if [ -e "$ans" ]
    then
        APP_DIR=$ans;
        break
    else
        echo "$ans doesn't exist"
    fi
  done
fi

echo "APP_DIR: $APP_DIR"

files="$APP_DIR/*"

for f in $files
do
    if [ -d "$f" ]
    then
        pushd $f >/dev/null
        
        PRJ_CONFIG=customizations/templates/WEB-INF/classes
        TEMPLATE=customizations/templates
        
        if [ -d $PRJ_CONFIG ]
        then
           # this is one project
           # only need to update the log4j.properties
           mv $PRJ_CONFIG/log4j.properties $PRJ_CONFIG/log4j.properties.1.0
           cp $LOG4J $PRJ_CONFIG
           echo "Project $f upgrade is done"
        elif [ -d $TEMPLATE ]
        then
           # this is one application
           # update the build.xml
           mv build.xml build.xml.1.0
           cp $BUILD .
           
           # update the log4j.properties
           mv $TEMPLATE/log4j.properties $TEMPLATE/log4j.properties.1.0
           cp $LOG4J $TEMPLATE
           echo "Application $f upgrade is done"
        else
           echo "$f is not a valid project or application"
        fi
        
        popd >/dev/null
    else
        echo " Warning: $f is not a valid application"
    fi
done
