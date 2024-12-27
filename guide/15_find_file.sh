#!/bin/bash
#findit
#function demo
function findit()
{
  if [ $# -lt 1 ];then
    echo "usage :findit file. "
    return 1
  fi

  for loop in "$@"
  do
    find /home/lance/ -name $loop -print;
  done

}

findit $@

# ./15_findit.sh 1_batch-rename.sh  2_for-test.sh 3_case-test.sh *.log

