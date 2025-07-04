# usage of sed
# -i: edit in place
# -e: edit
# -n: suppress output
# -f: read commands from file
# -r: use extended regular expressions
# -s: treat the string as a single line
# -u: use unbuffered input
# -v: show commands
# -w: write to file
# -E: use extended regular expressions

# Given n lines of credit card numbers, mask the first 12 digits of each credit card number with an asterisk (i.e., *) 
# and print the masked card number on a new line. 
# Each credit card number consists of four space-separated groups of four digits. 
# For example, the credit card number 1234 5678 9101 1234 would be masked and printed as **** **** **** 1234.

# Sample Input

#     1234 5678 9101 1234  
#     2999 5178 9101 2234  
#     9999 5628 9201 1232  
#     8888 3678 9101 1232 

# Sample Output
#     **** **** **** 1234  
#     **** **** **** 2234  
#     **** **** **** 1232  
#     **** **** **** 1232

sed 's/^\([0-9]\{4\}\) \([0-9]\{4\}\) \([0-9]\{4\}\)/**** **** ****/'
sed 's/[0-9]\{4\} /**** /g'
sed -E 's/[0-9]{4} /**** /g'

# Given an input file, with N credit card numbers, each in a new line, your task is to reverse the ordering of segments in each credit card number. Assume that the credit card numbers will have 4 space separated segments with 4 digits each.

# If the original credit card number is 1434 5678 9101 1234, transform it to 1234 9101 5678 1434.

# Useful References: This particular page on StackOverflow has a relevant example about sed, groups and backreferences. Here's a detailed tutorial covering groups and backreferences.

# Input Format
# N credit card numbers, each in a new line, credit card numbers will have 4 space separated segments with 4 digits each.

# Output Format
# N lines, each containing a credit card number with the ordering of its segments reversed.

sed -E 's/([0-9]{4}) ([0-9]{4}) ([0-9]{4}) ([0-9]{4})/\4 \3 \2 \1/'


# Task
# For each line in a given input file, transform all the occurrences of the word 'thy' with 'your'. The search should be case insensitive, i.e. 'thy', 'Thy', 'tHy' etc. should be transformed to 'your'.

# Input Format
# A text file will be piped into your command via STDIN.

# Output Format
# Transform and display the text as required in the task.

sed -i 's/thy/your/gi' file.txt  # -i: edit in place, need a file
sed 's/thy/your/gi'

sed 's/thy/\{thy\}/g' | sed 's/Thy/\{Thy\}/g'
sed 's/ the / this /'

