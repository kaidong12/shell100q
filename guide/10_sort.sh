#!/bin/bash
#command bachkup
# sort by $4
ls -l | awk '{if($5> 1000) print $1, $2, $3, $4, $5}' | sort -n +4

