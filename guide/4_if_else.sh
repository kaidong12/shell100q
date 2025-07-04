#!/bin/bash
#demo the usage of if
#ifdemo.t

if [ $(($# % 2)) -eq 0 ]; then
  echo $#
  echo "even number of parameters"

fi

DIRECTORY=$1
echo $DIRECTORY
#if [ "`ls -A $DIRECTORY`" = " " ]; then
if [ -z "`ls -A $DIRECTORY`" ]; then
    echo "$DIRECTORY is empty"
else
    echo "what do you want from me?"
fi

if [ ! -z "`ls -A $DIRECTORY`" ]; then
    echo "$DIRECTORY is not empty"
else
    echo "$DIRECTORY is empty"
fi

if [ -n "`ls -A $DIRECTORY`" ]; then
    echo "$DIRECTORY is not empty"
else
    echo "$DIRECTORY is empty"
fi

# Define a variable  
number=5

# Use if-elif-else to check the value of the variable  
if [ $number -eq 1 ]; then  
    echo "The number is 1."  
elif [ $number -eq 2 ]; then  
    echo "The number is 2."  
elif [ $number -eq 3 ]; then  
    echo "The number is 3."  
elif [ $number -gt 3 ] && [ $number -lt 6 ]; then  
    echo "The number is between 4 and 5."  
else 
    echo "The number is not 1, 2, 3, 4, or 5."  
fi