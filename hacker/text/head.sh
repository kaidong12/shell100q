# In this challenge, we practice using the head command to display the first n lines of a text file.
# Display the first 20 lines of an input file.

# usage of head
# head [OPTION]... [FILE]...
# -n [number] : print the first [number] lines
# -c [number] : print the first [number] bytes
# -q : suppress the header information
# -v : always print the header information
# -z : treat input and output data as text files, with line terminators (LF, CR, CRLF)

#!/bin/bash

# Enter your code here. Read input from STDIN. Print output to STDOUT
head -n 20

# Display the first 20 characters of an input file.
head -c 20

# Display the lines (from line number 12 to 22, both inclusive) of a given text file.
head -n 22 | tail -n +12
head -n 22 | tail -n 11

