#!/bin/bash

echo "===== $(date) - mode: $2, VM: $1 =====" >> /home/tester/yaml/logs/ifrename.log
vm=$1
mode=$2

function generatexml(){
  if [ "$1" == "dumpxml" ]; then
    virsh dumpxml "$2" > /tmp/"$2".xml
  else
    cp /home/tester/testbeds/tb/kvmconf/vms/"$2".xml /tmp/"$2".xml
  fi
}

function renameif(){
  echo "$(date) - VM name: $2" >> /home/tester/yaml/logs/ifrename.log
  generatexml $1 $2

  if [ "$2" == "ubuntu-services" ]; then
    awk '/<target dev='\''vnet[0-9]+'\''\/>/ {sub(/vnet[0-9]+/, "ubuntu-i-" i++)} { print }' /tmp/"$2".xml > /tmp/"$2".xml.new && sudo mv /tmp/"$2".xml.new /tmp/"$2".xml
  else
    awk -v suffix="$2" '/<target dev='\''vnet[0-9]+'\''\/>/ {sub(/vnet[0-9]+/, suffix "-i-" i++)} { print }' /tmp/"$2".xml > /tmp/"$2".xml.new && sudo mv /tmp/"$2".xml.new /tmp/"$2".xml
  fi

  #exit

  echo "destorying $2"
  virsh destroy $2
  sleep 10

  echo "create $2"
  virsh create /tmp/"$2".xml
  sleep 10

  #echo "define $2"
  #virsh define /tmp/"$2".xml
  #sleep 5

  #echo "starting $2"
  #virsh start $2
}

function dorange(){
  for ((i=1; i<=13;i++))
    do
      name="vm$i"
      if [ $i -eq 5 ]; then
        name="vm16"
      fi
      echo  "renameif" $mode "$name"
      renameif $mode "$name"
    done
}

if [ $vm == "range" ]; then
  dorange
elif [ $vm == "all" ]; then
  dorange

  echo "renameif" $mode "aastha"
  renameif $mode "aastha"

  echo "renameif" $mode "ubuntu-services"
  renameif $mode "ubuntu-services"

else
  echo "renameif" $mode $vm
  renameif $mode $vm
fi

