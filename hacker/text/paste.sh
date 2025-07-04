
#usage of paste command
# -d : delimiter
# -s : merge lines
# - : stdin


# Given a CSV file where each row contains the name of a city and its state separated by a comma, your task is to restructure the file in such a way, that three consecutive rows are folded into one, and separated by tab.

# Input Format
# You are given a CSV file where each row contains the name of a city and its state separated by a comma.

# Output Format
# Restructure the file in such a way, that every group of three consecutive rows are folded into one, and separated by tab.

paste - - -
paste -d '\t' - - -

# In this challenge, we practice using the paste command to merge lines of a given file.

# You are given a CSV file where each row contains the name of a city and its state separated by a comma. Your task is to replace the newlines in the file with semicolons as demonstrated in the sample.

# Input Format
# You are given a CSV file where each row contains the name of a city and its state separated by a comma.

# Output Format
# Replace the newlines in the input file with semicolons as demonstrated in the sample.

paste -sd ';' - - -

# In this challenge, we practice using the paste command to merge lines of a given file.
# You are given a CSV file where each row contains the name of a city and its state separated by a comma. Your task is to restructure the file so that three consecutive rows are folded into one line and are separated by semicolons.

# Input Format
# You are given a CSV file where each row contains the name of a city and its state separated by a comma.

# Output Format
# Restructure the file so that three consecutive rows are folded into one line and are separated by semicolons.

paste -d ';' - - -


