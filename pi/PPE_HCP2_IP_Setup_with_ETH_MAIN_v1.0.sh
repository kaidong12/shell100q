#!/bin/bash

sysctl -w net.ipv6.conf.all.forwarding=1

ip l a br1 type bridge
ip l a eth_main type bridge
ip l a l eth1 name eth1.4 type vlan id 4
ip l a v1 type veth peer name v1-br1
ip l s br1 up
ip l s eth_main up
ip l s eth1.4 up
ip l s v1-br1 up
ip l s eth1.4 master eth_main
ip l s v1-br1 master br1

ip a a fd53:7cb8:383:4::107/64 dev eth_main
ip a a fd53:7cb8:383:2::fc10/64 dev br1

ip l a v-gw type veth peer name v-gw-br-conmod
ip l s v-gw up
ip l s v-gw-br-conmod up
ip l s v-gw-br-conmod master eth_main
ip a a fd53:7cb8:383:4::fc10/64 dev v-gw

ip netns add ns1
ip l s v1 netns ns1
ip netns exec ns1 ip l s v1 up
ip netns exec ns1 ip a a fd53:7cb8:383:2::1:117/64 dev v1
ip netns exec ns1 ip -6 route add fd53:7cb8:383:4::/64 via fd53:7cb8:383:2::fc10

#Wait 10s
echo "waiting 10s ...until netwok configuration get fully started"
sleep 10

# Ping ConMod
echo "Trying to ping ConMod NAD domain /n"
ping -c 4 fd53:7cb8:383:4::1:1b5

echo "Trying to ping ConMod CD domain /n"
ping -c 4 fd53:7cb8:383:4::67

echo "Enjoy your journey mate /n/n"
