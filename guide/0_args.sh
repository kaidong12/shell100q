#!/bin/bash

# 1. 位置参数的基本用法
echo "脚本名称: $0"
echo "第一个参数: $1"
echo "第二个参数: $2"
echo "第二个参数: $3"
# 如果参数个数超过 9，需要用 ${} 来引用，例如 ${10}、${11}。

# 2. 特殊位置参数
echo "参数个数: $#"
echo "所有参数（会将每个参数作为独立的字符串处理）: $@"
echo "所有参数（会将所有参数作为一个字符串处理）: $*"
echo "上一个命令的退出状态: $?"
echo "当前脚本的 PID: $$"

# ./0_args.sh arg1 arg2 arg3
# 脚本名称: ./0_args.sh
# 第一个参数: arg1
# 第二个参数: arg2
# 参数个数: 3
# 所有参数（独立字符串）: arg1 arg2 arg3
# 所有参数（单个字符串）: arg1 arg2 arg3
# 上一个命令的退出状态: 0
# 当前脚本的 PID: 12345

# 3. 位置参数的遍历
for arg in "$@"; do
    echo "参数: $arg"
done

# 4. 位置参数的偏移
echo "第一个参数: $1"
shift
echo "第一个参数（shift 后）: $1"
shift
echo "第一个参数（shift 后）: $1"
shift
echo "第一个参数（shift 后）: $1"

# 5. 默认值设置
name1=${1:-"默认名称"}
echo "名称: $name1"
name4=${4:-"默认名称"}
echo "名称: $name4"

# 6. 函数中的位置参数
my_function() {
    echo "函数第一个参数: $1"
    echo "函数第二个参数: $2"
}

my_function "func_arg1" "func_arg2"

