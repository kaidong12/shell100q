# usage of grep command
# -i : case insensitive
# -E : extended regular expression
# -v : invert match
# -w : match whole word
# -c : count number of matches
# -l : list filenames with matches
# -n : display line numbers with matches
# -o : only display the matching part of the line
# -r : recursive search
# -s : suppress error messages
# -h : suppress the prefix of filenames
# -f : read patterns from a file
# -e : specify a pattern to search for
# -A : display the lines after the match
# -B : display the lines before the match

# 在文件中搜索包含"error"的行
grep "error" logfile.txt

# 在多个文件中搜索
grep "pattern" file1.txt file2.txt

# 忽略大小写搜索
grep -i "warning" messages.log

# 搜索以"start"开头的行
grep "^start" data.txt

# 搜索以"end"结尾的行
grep "end$" data.txt

# 搜索空行
grep "^$" file.txt

# 使用扩展正则表达式（匹配数字）
grep -E "[0-9]+" file.txt
grep -i -E "the|that|then|those"

# 显示匹配行及其前2行
grep -B 2 "exception" server.log

# 显示匹配行及其后2行
grep -A 2 "exception" server.log

# 显示匹配行及其前后各1行
grep -C 1 "critical" app.log

# 递归搜索目录中的所有文件
grep -r "function" /path/to/code/

# 只显示包含匹配项的文件名
grep -l "main" *.c

# 搜索时排除某些文件
grep "config" --exclude=*.tmp *

# 全词匹配（只匹配完整单词）
grep -w "word" file.txt

# 反向匹配（显示不包含模式的行）
grep -v "debug" output.log

# 同时搜索多个模式
grep -e "error" -e "warning" logs.txt

# 统计匹配行数
grep -c "success" results.csv

# 3. 复杂模式匹配
# 匹配IP地址
grep -E "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" logfile

# 匹配邮箱地址
grep -E "\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}\b" contacts.txt

# 匹配时间格式(HH:MM:SS)
grep -E "([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]" timestamps.log


# Task

# Given a text file, which will be piped to your command through STDIN, use grep to display all those lines which contain any of the following words in them:
# the
# that
# then
# those
# The search should not be sensitive to case. Display only those lines of an input file, which contain the required words.

# Input Format
# A text file with multiple lines will be piped to your command through STDIN.

# Output Format
# Display the required lines without any changes to their relative ordering.

grep -i -E -w "the|that|then|those" # -w : match whole word

# Current Task
# Given an input file, with N credit card numbers, each in a new line, your task is to grep out and output only those credit card numbers which have two or more consecutive occurences of the same digit (which may be separated by a space, if they are in different segments). Assume that the credit card numbers will have 4 space separated segments with 4 digits each.
# If the credit card number is 1434 5678 9101 1234, there are two consecutive instances of 1 (though) as highlighted in box brackets: 1434 5678 910[1] [1]234
# Here are some credit card numbers where consecutively repeated digits have been highlighted in box brackets. The last case does not have any repeated digits: 1234 5678 910[1] [1]234
# 2[9][9][9] 5178 9101 [2][2]34
# [9][9][9][9] 5628 920[1] [1]232
# 8482 3678 9102 1232

grep '\([0-9]\)\s*\1'




