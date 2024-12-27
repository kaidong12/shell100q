#! /bin/bash


function reverse()
{
  number=$1
  length=${#number}
  #echo $length

  result=''

  while [ $length -ge 0 ]
  do
    temp=${number:$length:1}
    #echo $temp
    result=$result$temp
    length=$((length-1))
    #echo $length
  done

  echo  $result

}

# You cannot return an arbitrary result from a shell function.
reverse $1


# ./16_reverse.sh 1234567
