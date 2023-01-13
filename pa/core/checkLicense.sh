#!/bin/sh

cat license.txt
while true; do
    read -p "Do you accept the above license terms? (yes or no) " yn
      case $yn in
          yes ) exit 0;;
          no ) exit 1;;
          * ) echo "Please answer yes or no.";;
      esac
done



