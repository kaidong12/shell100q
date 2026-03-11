#!/bin/bash

pushd /home/tester/images/26.1/topology_provided || exit 1
rm -rf viptela-bond-genericx86-64.qcow2 viptela-smart-genericx86-64.qcow2 viptela-vmanage-genericx86-64.qcow2 viptela-edge-genericx86-64.qcow2 regression.bin c8000v-regression.iso MD5SUMS
popd || exit 1

pushd /home/tester/images || exit 1
rm -rf viptela-bond-genericx86-64.qcow2 viptela-smart-genericx86-64.qcow2 viptela-vmanage-genericx86-64.qcow2 viptela-edge-genericx86-64.qcow2 regression.bin c8000v-regression.iso MD5SUMS
popd || exit 1

cd /home/tester/images
