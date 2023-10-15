#!/bin/bash
#opt2

echo "$(($#-2))"

while [ $# -ne 0 ]
do
  echo $1
  shift
done

eval echo $$#
eval echo \$$#


