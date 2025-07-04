#!/bin/bash

# printf 是 Bash 中用于格式化输出的命令，比 echo 更强大、更灵活。它支持精确控制输出格式（如对齐、浮点数、进制转换等），语法类似于 C 语言的 printf() 函数。

# printf 基本语法
# printf "格式字符串" [参数1] [参数2] ...

# %s：字符串
# %c：单个字符
# %d：十进制整数
# %f：浮点数
# %x：十六进制整数
# %X：大写十六进制整数
# %o：八进制整数
# %b：解释转义字符，将字符串中的转义字符（如 \n、\t）转换为对应的字符
# %p：指针，以十六进制形式输出指针地址

printf "Decimal: %d, Hex: %x, Octal: %o\n" 255 255 255

str="hello"
printf "|%-20s|\n" "$str"   # 左对齐，宽度 20


string="what is your selections?"

for word in $string
do
  len=${#word}
  if [ $len -lt 6 ]
  then
    pad=$((10 - len))

    right_padded_string=$(printf "%-10s" "$word" | tr " " "-")   # 右对齐，宽度 10
    echo $right_padded_string

    left_padded_string=$(printf "%10s" "$word" | tr " " "-")   # 左对齐，宽度 10
    echo $left_padded_string

  fi

done


# 打印一个边长为6的正三角形，边由*组成

for i in {1..6}
do
  for ((j=1; j<=6-i; j++))
  do
    printf " "
  done

  for ((k=1; k<=i; k++))
  do
    printf "* "
  done
  echo
done

