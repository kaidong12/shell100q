#! /bin/bash

:<<EOF
The special characters (meta-characters) used for defining regular expressions are:
* . ^ $ + ? ( ) [ ] | \ ' "
EOF

function valid_ip()

{
  local  ip=$1
  ip_stat=1

  if [[ $ip =~ ^[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}$ ]]; then
    # Old Internal Field Separatr
    OIFS=$IFS
    # Internal Field Separator
    IFS='.'
    # Split the string into an array using . as a separator
    ip=($ip)
    IFS=$OIFS
    [[ ${ip[0]} -le 255 && ${ip[1]} -le 255 && ${ip[2]} -le 255 && ${ip[3]} -le 255 ]]
    ip_stat=$?
  fi
    echo $ip_stat
}

valid_ip $1
