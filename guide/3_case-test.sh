#!/bin/bash
#case statement test
echo "pls enter a number between 1-3"
read NUMBER
case $NUMBER in
1)
    echo "The number you entered is: 1"
    ;;
2)
    echo "The number you entered is: 2"
    ;;
3)
    echo "The number you entered is: 3"
    ;;
y|Y)
    echo "you enter is: Y"
    ;;
*)
    echo "you enter is not a number 1-3;"
    echo "$(basename $0): This is wrong" >&2
    exit;
    ;;
esac
