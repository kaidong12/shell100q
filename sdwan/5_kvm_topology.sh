#!/usr/bin/env bash

OUT="kvm_topology.dot"

echo "digraph KVM {" > "$OUT"
echo "  rankdir=LR;" >> "$OUT"
echo "  node [shape=box, style=rounded];" >> "$OUT"

# --- Bridges and bridge members ---
declare -A BRIDGE_MEMBERS
while read -r line; do
    if [[ $line =~ ^[a-zA-Z0-9] ]]; then
        bridge=$(echo "$line" | awk '{print $1}')
        current_bridge=$bridge
    else
        iface=$(echo "$line" | awk '{print $1}')
        [[ -n $iface ]] && BRIDGE_MEMBERS["$iface"]="$current_bridge"
    fi
done < <(brctl show | tail -n +2)

# --- Libvirt networks -> bridges ---
declare -A NET_BRIDGE
for net in $(virsh net-list --all --name); do
    br=$(virsh net-dumpxml "$net" | grep "<bridge" | sed -n "s/.*name='\([^']*\)'.*/\1/p")
    [[ -n $br ]] && NET_BRIDGE["$net"]="$br"
done

# --- VM interfaces ---
for vm in $(virsh list --all --name); do
    echo "  \"$vm\" [shape=ellipse, color=blue];" >> "$OUT"

    virsh domiflist "$vm" | tail -n +3 | while read -r iface type source model mac; do
        [[ -z $iface ]] && continue

        echo "  \"$iface\" [shape=box, color=black];" >> "$OUT"
        echo "  \"$vm\" -> \"$iface\";" >> "$OUT"

        bridge="${BRIDGE_MEMBERS[$iface]}"
        if [[ -n $bridge ]]; then
            echo "  \"$bridge\" [shape=diamond, color=darkgreen];" >> "$OUT"
            echo "  \"$iface\" -> \"$bridge\";" >> "$OUT"
        fi
    done
done

# --- Host NICs attached to bridges ---
for iface in "${!BRIDGE_MEMBERS[@]}"; do
    bridge="${BRIDGE_MEMBERS[$iface]}"
    if [[ ! $iface =~ ^vnet ]]; then
        echo "  \"$iface\" [shape=box, color=red];" >> "$OUT"
        echo "  \"$iface\" -> \"$bridge\";" >> "$OUT"
    fi
done

echo "}" >> "$OUT"

echo "Topology written to $OUT"

