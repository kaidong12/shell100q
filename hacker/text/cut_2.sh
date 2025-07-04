# Given a tab delimited file with several columns (tsv format) print the first three fields.

# Input Format
# A tab-separated file with lines of ASCII text only.

# Output Format
# The output should contain N lines. For each line in the input, print the first three fields.


#!/bin/bash

# Read the file line by line
while read line; do
    # Split the line into fields using the tab character as the delimiter
    IFS='\t'
    fields=($line)
    
    # Print the first three fields
    echo "${fields[0]} ${fields[1]} ${fields[2]}"
done

while read line; do
    echo "$line" | cut -f 1-3
done

# Print the characters from thirteenth position to the end.
while read line; do
    echo "$line" | cut -c 13-
done

# Given a sentence, identify and display its fourth word. 
# Assume that the space (' ') is the only delimiter between words.

while read line; do
    echo "$line" | cut -d ' ' -f 4
done

# Given a sentence, identify and display its first three words. 
# Assume that the space (' ') is the only delimiter between words.

while read line; do
    echo "$line" | cut -d ' ' -f -3
done

# Given a tab delimited file with several columns (tsv format) print the fields from second fields to last field.
while read line; do
    echo "$line" | cut -f 2-
done