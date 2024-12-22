#!/bin/bash

ip l d br1
ip l d eth_main
ip l d eth1.4
ip l d v1-br1
ip l d v-gw
ip netns del ns1


#Wait 3s
echo "waiting 3s ...until netwok configuration get fully started"
sleep 3

echo "Network reset already !"
