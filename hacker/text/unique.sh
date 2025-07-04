# In this challenge, we practice using the uniq command to eliminate consecutive repetitions of a line when a text file is piped through it.
# Given a text file, remove the consecutive repetitions of any line.

# usage of unique
# uniq [options] [input [output]]

# options
# -c : print the number of occurrences of each line
# -d : only print repeated lines
# -u : only print unique lines
# -f : ignore the first n fields
# -s : ignore the first n characters
# -i : ignore case differences

uniq

# In this challenge, we practice using the uniq command to eliminate consecutive repetitions of a line when a text file is piped through it.

# Given a text file, count the number of times each line repeats itself. 
# Only consider consecutive repetitions. Display the space separated count and line, respectively. There shouldn't be any leading or trailing spaces. Please note that the uniq -c command by itself will generate the output in a different format than the one expected here.
uniq -c | cut -c 7-
uniq -c | sed 's/      //'

# Given a text file, count the number of times each line repeats itself (only consider consecutive repetions). Display the count and the line, separated by a space. There shouldn't be leading or trailing spaces. Please note that the uniq -c command by itself will generate the output in a different format.
# This time, compare consecutive lines in a case insensitive manner. So, if a line X is followed by case variants, the output should count all of them as the same (but display only the form X in the second column).
# So, as you might observe in the case below: aa, AA and Aa are all counted as instances of 'aa'.
uniq -ic | cut -c 7-

# Given a text file, display only those lines which are not followed or preceded by identical replications.
uniq -u

# Given a CSV file where each row contains the name of a city and its state separated by a comma, your task is to replace the newlines in the file with tabs as demonstrated in the sample.
# Input Format

# You are given a CSV file where each row contains the name of a city and its state separated by a comma.
# Output Format
# Replace the newlines in the input with tabs as demonstrated in the sample.

cat | tr '\n' '\t'
cat | xargs -I {} printf "%s\t" {}

