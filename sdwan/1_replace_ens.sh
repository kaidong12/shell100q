#!/bin/bash
# Interface name changed after upgrade, replace old interface names with new ones in configuration files.

# Define source and destination interface name arrays
src=(enp94s0f1 enp94s0f2 enp94s0f3 enp96s0f1 enp96s0f0 enp96s0f2 enp96s0f3 enp25s0f0 enp94s0f0)
dst=(ens2f1 ens2f2 ens2f3 ens3f1 ens3f0 ens3f2 ens3f3 ens1f0 ens2f0)

for i in "${!src[@]}"; do
    # find . -type f \( -name "*.yml" -o -name "*.yaml" \) -exec sed -i "s/${src[$i]}/${dst[$i]}/g" {} +
    echo "Replacing ${src[$i]} with ${dst[$i]}"
    sed -i "s/${src[$i]}/${dst[$i]}/g" *.yaml
done

# Dry run (verify before replacing)
for s in enp94s0f1 enp94s0f2; do
    grep -rn --include="*.yml" --include="*.yaml" "$s" .
done

echo "Replacement complete."
