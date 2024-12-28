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

