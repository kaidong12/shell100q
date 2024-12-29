#! /bin/bash
for f in `ls`
do
    # echo "-- $f"
    # if [[ $f =~ bakk.2.2.2 ]];
    if [[ $f =~ \.sh\.bakk$ ]];
    then
        echo $f
        nn=$(echo $f | sed 's/.2.2.2//')
        echo $nn
        mv $f $nn
    fi
done

# Rename all files with a `.txt` suffix in the current directory and its subdirectories to have a `.md` suffix:
# find . -type f -name "*.bak" -exec sh -c 'mv -i "$0" "${0%.bak}.mdd"' {} \;
