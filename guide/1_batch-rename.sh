#!/bin/sh
pre="00_"
i=0
for filename in `ls -lt *.sh`
do
  if [ -f $filename ]
  then
    i=$((i+1))
    if [ ${filename}.log != $filename ]
    then
      #mv $filename ./$i"_"${filename}
      mv $filename ./`echo $filename|sed "s/00/$i/"`
      echo `echo $filename|sed "s/00/$i/"`
    fi
  fi
done
