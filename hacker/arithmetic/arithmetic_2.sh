#!/bin/bash

# Given N integers, compute their average, rounded to three decimal places.

# Input Format
# The first line contains an integer, N.
# Each of the following N lines contains a single integer.

# Output Format
# Display the average of the N integers, rounded off to three decimal places.

read loop

divid=$loop
express="0"

while [ $loop -gt 0 ]
do
    read temp
    express=$express+$temp
    ((loop--))
done

express="("$express")"/$divid

result=$(echo "scale=10; $express" | bc -l)
result2=$(printf "%.3f" $result)
echo $result2
