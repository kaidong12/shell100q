
# option of cut
# -b : Display only the bytes in the specified range.
# -c : Display only the characters in the specified range.
# -d : Use the specified delimiter instead of the default tab character.
# -f : Display only the fields in the specified range.

# 提取第3-5个字符
echo "abcdefgh" | cut -c 3-5

# 提取多个不连续字符
echo "abcdefgh" | cut -c 1,3,5

# 基本字段提取（默认TAB分隔）
echo -e "apple\tbanana\tcherry" | cut -f 2
echo "$line" | cut -f 1-3

# 指定分隔符（如逗号）
echo "John,Doe,25" | cut -d ',' -f 1,3

# 处理CSV文件
cut -d ',' -f 1,3 data.csv

# 分析日志文件
cut -d ' ' -f 5 access.log

# 处理/etc/passwd
cut -d ':' -f 1 /etc/passwd


# Display the 2th and 7th character from each line of text.

# Input Format
# A text file with  lines of ASCII text only.

# Output Format
# The output should contain  lines. Each line should contain just two characters at the  and the  position of the corresponding input line.

# Sample Input
# Hello
# World
# how are you

# Sample Output
# e
# o
# oe

#!/bin/bash

while read line
do
    echo $line | cut -c 2,7 # 2nd and 7th character
    echo $line | cut -c 2-7 # 2nd to 7th character
done

# Display the first four characters from each line of text.
while read line
do
    echo $line | cut -c 1-4
done
