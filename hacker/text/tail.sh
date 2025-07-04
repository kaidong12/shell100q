# usage of tail
# tail [OPTION]... [FILE]...
# -n [number] : print the last [number] lines
# -c [number] : print the last [number] bytes
# -q : suppress the header information
# -v : always print the header information

tail -n +N  # 表示"从第N行开始"
tail -n N   # 表示"最后N行"

# In this challenge, we practice using the tail command to display the last n lines of a text file.

# Display the last 20 lines of an input file.
tail -n 20 input.txt

# Display the last 20 characters of an input file.
tail -c 20 input.txt
