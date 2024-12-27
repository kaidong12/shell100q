#!/bin/bash
function is_it_a_directory()
{
  #is_it_a_directory
  #check if the specific object is a directory
  if [ $# -lt 1 ]; then
    echo "is_it_a_directory: I need a argument."
    return 1
  fi

  _DIRECTORY_NAME=$1
  if [ ! -d $_DIRECTORY_NAME ]; then
    echo "no, it is not a directory"
    return 1
  else
    echo "yes, it is a directory"
    return 0
  fi
}

is_it_a_directory $1
