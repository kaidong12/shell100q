#! /bin/bash
# Rename all files with a `.sh.bakk` suffix in the current directory and its subdirectories to have a `.sh.bakk.2` suffix:

set -e
pushd /home/pi/debug/test
for f in `ls`
do
    # echo "-- $f"
    # if [[ $f =~ bakk.2.2.2 ]]
    # if [[ $f =~ \.sh\.bakk$ ]]
    # if [[ $f =~ \.sh\.bakk\.2$ ]]
    if [[ $f =~ \.sh\.bakk\.[0-9]$ ]]
    then
        echo $f
        # nn=$(echo $f | sed 's/.2.2.2//')
        # nn=$(echo $f | sed 's/.2/.3/')
        nn=$(echo $f | sed 's/.3/.4/')
        echo $nn
        mv $f $nn
    fi
done
popd

# Rename all files with a `.txt` suffix in the current directory and its subdirectories to have a `.md` suffix:
# find . -type f -name "*.bak" -exec sh -c 'mv -i "$0" "${0%.bak}.mdd"' {} \;
# find . -type f -name "*.mdd" -exec bash -c 'f="$0"; mv -i "$f" "${f%.mdd}.mm"' {} \;
