#!/bin/sh

###############################################################################
# This script contains common utilities
###############################################################################


can_connectdb() {
  DB=$1
  IP=$2
  PORT=$3
  USER=$4

  psql -h $IP -p $PORT -U $USER -d $DB  -c "SELECT 1"  2>&1 >/dev/null  | grep -q "FATAL"
  RESULT=$?   # grep will return 0 if it finds 'failure',  non-zero if it didn't 
  if [ $RESULT -eq 0 ]; then
      return 1
  fi
  psql -h $IP -p $PORT -U $USER -d $DB  "-c SELECT 1" 2>&1 >/dev/null  | grep -q "could not connect to server"
  RESULT=$?   # grep will return 0 if it finds 'failure',  non-zero if it didn't 
  if [ $RESULT -eq 0 ]; then
      return 1
  fi
  psql -h $IP -p $PORT -U $USER -d $DB  "-c SELECT 1" 2>&1 >/dev/null  | grep -q "service not known"
  RESULT=$?   # grep will return 0 if it finds 'failure',  non-zero if it didn't 
  if [ $RESULT -eq 0 ]; then
      return 1
  fi

  return 0
}


#return 0 for yes, 1 for no
get_user_reply() {

  while true; do
      read -p "$1 (yes or no)" yn
      case $yn in
          [yes]* ) return 0;;
          [no]* ) return 1;;
          * ) echo "Please answer yes or no.";;
      esac
  done
}
 
check_dbreset() {
  can_connectdb $1 $2 $3 $4
  if [ $? = 0 ]; then
    get_user_reply "$5"
    return $?
  fi
  return 0
}



