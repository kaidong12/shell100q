# Given a list of countries, each on a new line, your task is to read them into an array and then display the entire array, with a space between each of the countries' names.

# Recommended References
# Here's a great tutorial tutorial with useful examples related to arrays in Bash.

# Input Format
# A list of country names. The only characters present in the country names will be upper or lower case characters and hyphens.

# Output Format
# Display the entire array of country names, with a space between each of them.

#！/ bin/bash

# Read the list of countries into an array
readarray -t countries

# Display the entire array of country names, with a space between each of them
echo "${countries[@]}"

##########################################
names=()
i=0
while read name; do
    names[$i]=$name
    ((i++))
done
echo ${names[@]}

# 数组长度
echo "元素个数: ${#names[@]}"

# 遍历数组
for ((i=0; i<${#names[@]}; i++)); do
    echo ${names[$i]}
done

# 基本用法
function process_logs() {
    local logs=()
    
    # 添加元素
    logs+=("item1")
    logs[1]="item2"  # 索引从0开始
    logs+=("item3")
    
    # 获取元素
    echo "第一个元素: ${logs[0]}"
    
    # 数组长度
    echo "元素个数: ${#logs[@]}"
    
    # 遍历数组
    for item in "${logs[@]}"; do
        echo "内容: $item"
    done
}

process_logs
# 函数外部无法访问 logs 数组

# 结合命令输出
function get_files() {
    local files=()
    # 将find命令结果存入数组
    mapfile -t files < <(find . -name "*.log")
    
    echo "找到 ${#files[@]} 个日志文件:"
    printf "  - %s\n" "${files[@]}"
}


