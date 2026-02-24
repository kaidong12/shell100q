#!/bin/bash

echo "$(date) - Hook called with action: $1, VM name: $2" >> /var/log/libvirt/hooks.log
if [ "$1" == "start" ]; then
  # Change vnet to vmnet dynamically
  virsh dumpxml "$2" > /tmp/"$2".xml
  if [ "$2" == "ubuntu-services" ]; then
    sed -i "s/<target dev='vnet/<target dev='ubuntu-vnet/g" /tmp/"$2".xml
  else
    sed -i "s/<target dev='vnet/<target dev='$2-vnet/g" /tmp/"$2".xml
  fi

  echo "destorying $2"
  virsh destroy $2
  sleep 30
  
  echo "define $2"
  virsh define /tmp/"$2".xml
  sleep 5

  echo "starting $2"
  virsh start $2

fi
