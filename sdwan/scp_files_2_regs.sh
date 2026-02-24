#!/bin/bash

hostname=$1

function scp_files(){
    local host=$1
    echo "Copying files to $host..."

    scp .bash_aliases tester@"$host":/home/tester/

    scp bvirsh tester@"$host":/home/tester/bin/
    scp ifrename tester@"$host":/home/tester/bin/
    scp notify_bot tester@"$host":/home/tester/bin/

    scp 2601_notification_manager.py tester@"$host":/home/tester/kaidyan/scripts/
    scp poll_run_status.sh tester@"$host":/home/tester/kaidyan/scripts/

    # -- config files --
    # scp ntp.conf tester@"$host":/home/tester/kaidyan/scripts/
}

hosts=(10.74.6.134 10.75.28.83 10.74.6.141 10.124.10.233 10.74.5.23)
hostnames=(sdwan-reg-1 sdwan-reg-2 sdwan-reg-3 sdwan-reg-4 sdwan-reg-5)

if [ "$hostname" == "all" ]; then
    for index in "${!hosts[@]}"; do
        host="${hosts[$index]}"
        echo "Processing host: ${hostnames[$index]} (${host})"

        scp_files "$host"
        echo ""
    done
elif [[ "$hostname" == sdwan-reg-* ]]; then
    for index in "${!hosts[@]}"; do
        if [[ "${hostnames[$index]}" == "$hostname" ]]; then
            host="${hosts[$index]}"
            break
        fi
    done
    echo "Processing host: ${hostnames[$index]} (${host})"
    scp_files "$host"
else
    echo "Usage:"
    echo "  $0 [all|sdwan-reg-1|sdwan-reg-2|sdwan-reg-3|sdwan-reg-4|sdwan-reg-5]"
    exit 1
fi

echo "Done."

