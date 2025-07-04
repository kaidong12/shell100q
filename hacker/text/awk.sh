# usage of awk
# -f filename
# -F separator

# print the first column
awk '{print $1}' file.txt

# print the first and third column
awk '{print $1, $3}' file.txt

# print the first and third column, separated by a comma
awk '{print $1 "," $3}' file.txt

# You are given a file with four space separated columns containing the scores of students in three subjects. The first column contains a single character (), the student identifier. The next three columns have three numbers each. The numbers are between  and , both inclusive. These numbers denote the scores of the students in English, Mathematics, and Science, respectively.
# Your task is to identify those lines that do not contain all three scores for students.

# Input Format
# There will be no more than  rows of data.
# Each line will be in the following format:
# [Identifier][English Score][Math Score][Science Score]

# Output Format
# For each student, if one or more of the three scores is missing, display:

# Not all scores are available for [Identifier]

awk '{if (NF != 4) print "Not all scores are available for " $1 }'
awk '{if (NF < 4) print "Not all scores are available for " $1}'

# You are given a file with four space separated columns containing the scores of students in three subjects. The first column contains a single character (), the student identifier. The next three columns have three numbers each. The numbers are between  and , both inclusive. These numbers denote the scores of the students in English, Mathematics, and Science, respectively.

# Your task is to identify whether each of the students has passed or failed.
# A student is considered to have passed if (s)he has a score  or more in each of the three subjects.

# Input Format
# There will be no more than  rows of data.
# Each line will be in the following format:
# [Identifier][English Score][Math Score][Science Score]

# Output Format
# Depending on the scores, display the following for each student:
# [Identifier] : [Pass] 
# or
# [Identifier] : [Fail]  

awk '{if ($2 >= 50 && $3 >= 50 && $4 >= 50) print $1" : Pass"; else print $1" : Fail"}'

