#!/bin/bash

# The colons after p and d indicate that they require an argument.
# In this example, the options -p and -d take arguments and -h does not.

while getopts ":hp:d:" opt 
# -h : no argument
# -p: : requires an argument
# -d: : requires an argument
do
do
  case $opt in
    h )
      echo "Usage: my_script.sh [-h] [-p project-name] [-d dir]"
      exit 0
      ;;
    p )
      project_name=$OPTARG
      ;;
    d )
      directory=$OPTARG
      ;;
#    \? )
    * )
      echo "Invalid Option: -$OPTARG" 1>&2
      exit 1
      ;;
    : )
      echo "Invalid Option: -$OPTARG requires an argument" 1>&2
      exit 1
      ;;
  esac
done

echo "Project Name: ${project_name}"
echo "Directory: ${directory}"

# ./my_script.sh -h # displays help message
# ./my_script.sh -p my_project -d ~/projects # sets project name and directory
# ./my_script.sh -d # error: requires an argument
# ./my_script.sh -z # error: invalid option
