#!/bin/bash
#for statement test

set -x
for loop in what is you selections?
do
  cho $loop
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
