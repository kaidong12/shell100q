#!/bin/bash
#for statement test

set -x
for loop in what is you selections?
do
  echo $loop
done

set +x


string="what is your selections?"

for word in $string
do
  # echo $word
  echo ${#word}
  if [ ${#word} -gt 6 ]; then
    echo $word
  fi
done


for i in {0..100}  
do  
    if [ $((i % 3)) -eq 0 ]  
    then  
        echo $i  
    fi  
done


