#!/bin/bash

while [ 1 -eq 1 ]
do
  for f in `find . -name "*.pcap"`
  do
    /usr/bin/tcpreplay -i eth1 -t $f
    sleep 1
  done
done


i=1

while [ $i -lt 100 ]
do
  sleep 1
  echo $i
  i=$(($i+1))

done

