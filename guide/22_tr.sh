#!/bin/bash

# tr（translate）是 Linux/Unix 下的一个命令行工具，用于字符替换、删除或压缩重复字符。
# tr 命令的基本语法如下：
# tr [options] set1 set2

# 常用选项：
# -c, -C: 取补集
# -d: 删除指定字符
# -s: 压缩重复字符
# -t: 将 set1 中的字符替换为 set2 中的字符

# 示例：

echo "hello world" | tr 'a-z' 'A-Z'  # 将小写字母替换为大写字母：HELLO WORLD
echo "hello" | tr 'helo' '1234'      # 12334
echo "hello world" | tr -t 'a-z' 'A-Z'  # 将小写字母替换为大写字母：HELLO WORLD

echo "hello world" | tr -d 'aeiou'  # 删除所有元音字母：hll wrld
echo "hello world" | tr -d ' '  # 删除所有空格：helloworld

echo "hello world" | tr -s 'l'  # 压缩连续的 'l' 字符：helo world

echo "hello world" | tr -c 'a-z' 'A-Z'  # 将非小写字母替换为大写字母： helloZworldK
echo "hello world" | tr -C 'a-z' 'A-Z'  # 将非小写字母替换为大写字母： helloZworldK

echo "hello 123" | tr -cd 'a-z'  # -c 表示“补集”，-d 表示删除，即“保留所有字母，删除其他字符”：hello

cat /dev/urandom | tr -cd 'a-zA-Z0-9' | head -c 12  # 生成一个随机字符串：aBcDeFgHiJk

tr -s '\n' < input.txt > output.txt  # 删除文件中的空行：将 input.txt 中的连续换行符压缩为一个换行符，并将结果输出到 output.txt 中
