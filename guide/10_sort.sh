#!/bin/bash
#command bachkup

# -n: sort numerically
# -r: reverse order
# -f: ignore case
# -u: unique lines
# -V: sort by version number
# -h: human-readable

# -t C: 指定列分隔符为 C
# -k F: 按第 F 列排序
# -k F.S: 从第 F 列第 S 字符开始排序

# sort by $2
ls -l | awk '{if($5> 1000) print $1, $2, $3, $4, $5}' | sort -nk2
ls -l | awk '{if($5> 1000) print $1, $2, $3, $4, $5}' | sort -nrk2

# 对CSV文件按第3列数值排序
sort -t ',' -k 3n data.csv

# 对日志按第4列IP排序
sort -k 4 access.log

# 多级排序：先按第2列数值，再按第1列字典序
sort -k 2n -k 1 data.txt


