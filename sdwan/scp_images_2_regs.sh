#!/bin/bash

# scp_images_2_regs.sh <sdwan-reg-x> <images_folder_name> <version> <build_number>
# ./scp_images_2_regs.sh sdwan-reg-2 regression_images_hydra 26.2 5060
# ./scp_images_2_regs.sh sdwan-reg-3 regression_images_styxL 26.2 5094
# ./scp_images_2_regs.sh sdwan-reg-4 regression_images_Styx 26.1 150

hostnames=(sdwan-reg-1 sdwan-reg-2 sdwan-reg-3 sdwan-reg-4 sdwan-reg-5)
hosts=(10.74.6.134 10.75.28.83 10.74.6.141 10.124.10.233 10.74.5.23)

hostname=$1
folder=$2
version=$3
build=$4

path="/auto/sdwan2/builds/daily/$version/$build"
path_vedge="/auto/sdwan2/builds/daily/20.9/STABLE/"
dest="/home/tester/images/$folder"

function scp_vedge_image(){
    pushd "$path_vedge" || { echo "Invalid path: $path_vedge"; exit 1; }
    local host=$1
    echo "Copying vedge image to $host..."

    scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null viptela-edge-genericx86-64.qcow2 tester@"$host":${dest}/
    
    echo "Completed copying vedge image to $host."
    popd || exit
}

function scp_controller_image(){
    pushd "$path" || { echo "Invalid path: $path"; exit 1; }
    local host=$1
    echo "Copying image to $host..."

    # echo "scp viptela-vmanage-genericx86-64.qcow2 ..."
    # scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null viptela-vmanage-genericx86-64.qcow2 tester@"$host":${dest}/

    # echo "scp c8000v-universalk9_serial.26.*.iso ..."
    # scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null c8000v-universalk9_serial.26.*.iso tester@"$host":${dest}/

    # echo "scp viptela-smart-genericx86-64.qcow2 ..."
    # scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null viptela-smart-genericx86-64.qcow2 tester@"$host":${dest}/

    # echo "scp viptela-bond-genericx86-64.qcow2 ..."
    # scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null viptela-bond-genericx86-64.qcow2 tester@"$host":${dest}/

    # echo "scp MD5SUMS ..."
    # scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null MD5SUMS tester@"$host":${dest}/

    echo "scp controller images ..."
    scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null viptela-vmanage-genericx86-64.qcow2 \
        viptela-smart-genericx86-64.qcow2 \
        viptela-bond-genericx86-64.qcow2 \
        MD5SUMS \
        c8000v-universalk9_serial.26.*.iso \
        cEdge/c8kg2be-*.bin \
        tester@"$host":${dest}/

    echo "Completed copying images to $host."
    popd || exit
}

if [[ "$hostname" == sdwan-reg-* ]]; then
    for index in "${!hosts[@]}"; do
        if [[ "${hostnames[$index]}" == "$hostname" ]]; then
            host="${hosts[$index]}"
            break
        fi
    done
    
    echo "Processing host: ${hostnames[$index]} (${host})"
    scp_vedge_image "$host"
    scp_controller_image "$host"
else
    echo "Usage:"
    echo "  $0 [sdwan-reg-1|sdwan-reg-2|sdwan-reg-3|sdwan-reg-4|sdwan-reg-5] [images_folder_name] [version] [build_number]"
    exit 1
fi

echo "All done."
