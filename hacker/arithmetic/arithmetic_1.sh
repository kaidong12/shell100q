#!/bin/bash

# A mathematical expression containing +,-,*,^, / and parenthesis will be provided. 
# Read in the expression, then evaluate it. Display the result rounded to 3 decimal places.

read -r expression

# Remove whitespace from the expression
expression=$(echo "$expression" | tr -d ' ')

# Evaluate the expression using bc
result=$(echo "scale=5; $expression" | bc -l)

result2=$(printf "%.3f" "$result")
# Print the result
echo "$result2"

#################################################################################

read -r exp

result=$(echo "scale=10; $exp" | bc -l) 
# scale=10
# 设置 bc 计算时的小数位数为 10（仅影响除法、平方根等运算，不影响整数运算）。
# 例如：3/2 会输出 1.5000000000（共 10 位小数）。
# 
# bc -l
# -l 选项加载数学库（支持 sin()、cos()、log() 等函数），但在这里主要用于启用浮点运算。

round_result=$(printf "%.3f" "$result")
# printf "%.3f" "$result" 
# 将结果格式化为 3 位小数。

echo $round_result