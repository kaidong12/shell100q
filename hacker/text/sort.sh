# -n: sort numerically
# -r: reverse order
# -f: ignore case
# -u: unique lines
# -V: sort by version number
# -h: human-readable

# -t C: 指定列分隔符为 C
# -k F: 按第 F 列排序
# -k F.S: 从第 F 列第 S 字符开始排序

sort -r -n -k 2 -t $'\t'
sort -r -n -k 2 -t $'\t' -k 3 -t $'\t'
sort -r -n -k 2 -t $'\t' -k 3 -t $'\t' -k 4 -t $'\t'
$'\t' 是 Bash 中表示制表符的特殊语法
复杂排序：-k 2,2n -k 3,3r（先按第2列数值升序，再按第3列降序）

cat web.log | sort -r -n -k 4 -t ' '
sort -t ',' -n -k 5 sales.csv
# 按内存使用降序排列进程
ps aux | sort -r -n -k 4

# In this challenge, we practice using the sort command to sort input in text or TSV formats.
# Given a text file, order the lines in lexicographical order.

sort

# Given a text file, order the lines in reverse lexicographical order (i.e. Z-A instead of A-Z).
sort -r

# In this challenge, we practice using the sort command to sort input in text or TSV formats.

# You are given a text file where each line contains a number. 
# The numbers may be either an integer or have decimal places. 
# There will be no extra characters other than the number or the newline at the end of each line. 
# Sort the lines in ascending order - so that the first line holds the numerically smallest number, and the last line holds the numerically largest number.

# Input Format
# A text file where each line contains a positive number (less than ) as described above.

# Output Format
# Output the text file with the lines reordered in numerically ascending order.

sort -n


# You are given a file of text, where each line contains a number (which may be either an integer or have decimal places). There will be no extra characters other than the number or the newline at the end of each line. Sort the lines in descending order - - such that the first line holds the (numerically) largest number and the last line holds the (numerically) smallest number.

# Input Format
# A text file where each line contains a number as described above.

# Output Format
# The text file, with lines re-ordered in descending order (numerically).

sort -rn

# You are given a file of text,which contains temperature information about American cities, in TSV (tab-separated) format. 
# The first column is the name of the city and the next four columns are the average temperature in the months of Jan, Feb, March and April (see the sample input). 
# Rearrange the rows of the table in descending order of the values for the average temperature in January.

# Input Format
# A text file where each line contains a row of data as described above.

# Output Format
# Rearrange the rows of the table in descending order of the values for the average temperature in January (i.e, the mean temperature value provided in the second column).

sort -r -n -k 2 -t $'\t'

# You are given a file of tab separated weather data (TSV). There is no header column in this data file.
# The first five columns of this data are: (a) the name of the city (b) the average monthly temperature in Jan (in Fahreneit). (c) the average monthly temperature in April (in Fahreneit). (d) the average monthly temperature in July (in Fahreneit). (e) the average monthly temperature in October (in Fahreneit).

# You need to sort this file in ascending order of the second column (i.e. the average monthly temperature in January).

# Input Format
# A text file with multiple lines of tab separated data. The first five fields have been explained above

# Output Format
# Sort the data in ascending order of the average monthly temperature in January.

sort -k 2 -n -t $'\t'


# You are given a file of pipe-delimited weather data (TSV). There is no header column in this data file. The first five columns of this data are: (a) the name of the city (b) the average monthly temperature in Jan (in Fahreneit). (c) the average monthly temperature in April (in Fahreneit). (d) the average monthly temperature in July (in Fahreneit). (e) the average monthly temperature in October (in Fahreneit).
# You need to sort this file in descending order of the second column (i.e. the average monthly temperature in January).

# Input Format
# A text file with multiple lines of pipe-delimited data. The first five fields have been explained above

# Output Format
# Sort the data in descending order of the average monthly temperature in January.

sort -k 2 -n -r -t '|'


