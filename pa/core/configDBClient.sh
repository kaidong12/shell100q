#!/bin/sh

source ./common.sh



pushd $TRUVISO_HOME
cd TruCQ/bin
if [ $? -ne 0 ]; then
    err_exit "Unexpected error during truviso client install"
fi
mkdir .nop
mv * .nop
mv .nop/psql .
mv .nop/pg_restore .
mv .nop/pg_dump .
chmod a-r .nop
popd
exit 0

