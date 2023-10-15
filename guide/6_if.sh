#!/bin/bash
#demo the usage of if
#ifdemo.t

DIRECTORY=$1

echo $DIRECTORY

#if [ "`ls -A $DIRECTORY`" = " " ]; then
if [ ! -z "`ls -A $DIRECTORY`" ]; then
    echo "$DIRECTORY is empty"
else
    echo "what do you want from me?"
fi

