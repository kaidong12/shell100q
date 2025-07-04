#! /bin/bash

# 在 Bash 中，declare -A grid 是用于声明一个关联数组（Associative Array）的命令。
# declare：Bash 的内置命令，用于声明变量或设置变量属性。
# -A：选项，表示要声明的是一个关联数组（类似其他语言中的字典或哈希表）。
# grid：数组的名称，你可以替换为任何有效的变量名。

declare -A grid
rows=3
cols=3

# 初始化 3x3 网格
for ((i=0; i<rows; i++)); do
    for ((j=0; j<cols; j++)); do
        grid["$i,$j"]="."  # 填充默认值
    done
done

# 修改第2行第3列（从0开始计数）
grid["1,2"]="X"

# 打印网格
for ((i=0; i<rows; i++)); do
    for ((j=0; j<cols; j++)); do
        printf "%s " "${grid["$i,$j"]}"
    done
    echo
done
