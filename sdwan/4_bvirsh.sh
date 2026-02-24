#!/bin/bash

op=$1
vm=$2

function virsh_vm_range(){
  for ((i=1; i<=13;i++))
  do
    name="vm"$i
    if [ $i -eq 5 ]; then
      name="vm16"
    fi
    echo  "virsh $op $name"
    virsh $op $name
  done
}

if [ $vm == "range" ]; then
  virsh_vm_range
elif [ $vm == "all" ]; then
  virsh_vm_range

  echo "virsh $op vm16"
  virsh $op "vm16"
  echo "virsh $op aastha"
  virsh $op "aastha"
  echo "virsh $op ubuntu-services"
  virsh $op "ubuntu-services" 
else
  echo "virsh $op $vm"
  virsh $op $vm
fi


