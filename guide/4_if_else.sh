#!/bin/bash
#demo the usage of if
#ifdemo.t

if [ $(($# % 2)) -eq 0 ]; then
  echo $#
  echo "even number of parameters"

fi



DIRECTORY=$1

echo $DIRECTORY

if [ -z "`ls -A $DIRECTORY`" ]; then
  echo "$DIRECTORY is empty"
else
  echo "$(ls -l $DIRECTORY)"
fi

