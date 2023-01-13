#!/bin/sh
if [ $1 -eq $1 2>/dev/null ] && [ $1 -le 65535 ] && [ $1 -ge 1 ]
then
    java -classpath /tmp/validateutils.jar com.cisco.pa.install.InstallValidation $1
    exit $?
else
    exit 1
fi


