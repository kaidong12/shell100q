# Your task is to use for loops to display only odd natural numbers from 1 to 99.

#!/bin/bash

for ((i=1;i<=99;i++))
do
    rmd=$((i%2))
    # echo $rmd
    if [ $rmd -eq 1 ];then
        echo $i
    fi
done

# Use a for loop to display the natural numbers from  to .
for i in {1..50}
do
    echo $i
done