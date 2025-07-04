#!/bin/sed -f
#all comment lines must start with a hash '#'
#name:sed.sh
#to call: ./sed.sh testcase.log


#2p

#1,3p

#/^d/p


#print the content between 20 to /sys/
#20,/sys/p
#1,$p


#only display the line number
#20,/sys/=


####################################
#20p
#/sys/=
#/.*conf/p


#append text
#/sys/ a\ \nhello, there is a system parameter emerged!!!!!!!!!!!\n

#insert text before current line
#/sys/ i\ \nhaha, there is a system parameter emerging!!!!!!!!!!!!\n


#modify the context
#/sys/ c\ hoho, the original text has been changed!!!!!!!!!!!



#replace text
#s/root/lance/g


#output to another file
#s/root/lance/w sed.out


#use & to record the fileds
#s/root/haha, i'm &\t/g


#read text from another file and append to the next few lines
#/sys/r cpucase.log


#match and quit
#/sys/q


#display the control character #l
1,$l

###################################
# sed（Stream Editor）是 Linux/Unix 下的流式文本编辑器，通过选项和命令组合实现高效的文本处理。
###################################

# 常用选项：
# -e：允许使用多个命令。
# -f：从文件中读取命令。
# -i：直接修改文件内容，而不是输出到标准输出。
# -n：只输出匹配到的行，不输出其他行。

# 常用命令：
# a：在当前行之后追加文本。
# c：用新文本替换匹配到的行。
# d：删除匹配到的行。
# i：在当前行之前插入文本。
# p：打印匹配到的行。
# s：替换匹配到的文本。
# w：将匹配到的行写入文件。

echo "hello world" | sed 's/hello/hi/'  # 输出: hi world

sed -i 's/old/new/' file.txt  # 直接修改文件内容

sed -n '/pattern/p' file.txt  # 只显示匹配到模式的行

# 多命令组合
echo "abc123" | sed -e 's/abc/ABC/' -e 's/123/456/'  # 输出: ABC456


