#!/bin/sh
source /etc/sysconfig/primeanalytics/primea
export ANT_HOME=$ANT_HOME
export JAVA_HOME=$JAVA_HOME
export TRUVISO_HOME=$TRUVISO_HOME
export PA_HOME=$PA_HOME
export PATH=$ANT_HOME/bin:$JAVA_HOME/bin:$TRUVISO_HOME/TruCQ/bin:$PATH
if [ -e "$PA_HOME/biplatform" ]; then 
    export BIPLATFORM_HOME=$PA_HOME/biplatform
    export PA_INSTALLED_LICENSE_PATH=$PA_HOME/biplatform/.installedLicenses.xml
fi




