# In this challenge, we practice using the sort command to sort input in text or TSV formats.

# Given a text file, order the lines in reverse lexicographical order (i.e. Z-A instead of A-Z).

# Input Format

# A text file.

# Output Format

# Output the text file with the lines reordered in reverse lexicographical order.

#!/bin/bash

# echo option -e to print special characters
# -e    enable interpretation of backslash escapes
# -n    suppress trailing newline

touch input.txt
while IFS= read -r line; do
    echo -e $line >> input.txt
done

sort -r input.txt
rm -rf input.txt

################################################
sort -r

