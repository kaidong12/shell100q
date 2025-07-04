
#whois
#get the user name of a specific ID

function whois(){
  if [ $# -lt 1 ]; then
    echo "whois : need user id, please"
    return 1
  fi

  for loop in $@
  do
    _USER_NAME=`grep $loop /etc/passwd | awk -F: '{print $5}'`
    if [ -z "$_USER_NAME" ]; then
      echo "whois: Sorry cannot find $loop"
    else
      echo "$loop is $_USER_NAME"
    fi
  done

}

whois $*
whois $@

# ./13_whois.sh root lance ftp

