在 Bash 中，关联数组（Associative Array） 是一种特殊的数据结构，
允许使用任意字符串作为键（key）来存储和访问值（value），
类似于其他编程语言中的字典（Dictionary）或哈希表（Hash）。
它是 Bash 4.0 及以上版本引入的功能。

# 1, 必须显式声明类型：
declare -A my_dict  # -A 表示关联数组

# 2, 基本操作

my_dict["name"]="Alice"
my_dict["age"]=25
my_dict["job"]="Engineer"


# 3, 访问元素
echo ${my_dict["name"]}  # 输出: Alice
echo ${my_dict["age"]}   # 输出: 25
echo ${my_dict["job"]}   # 输出: Engineer

# 4, 遍历元素
for key in "${!my_dict[@]}"; do
    echo "$key: ${my_dict[$key]}"
done

# 遍历所有键值对
for key in "${!my_dict[@]}"; do
    echo "$key => ${my_dict[$key]}"
done


# 5, 删除元素
unset my_dict["name"]

# 6, 检查键是否存在
if [[ -v my_dict["age"] ]]; then
    echo "Key 'age' exists."
else
    echo "Key 'age' does not exist."
fi

# 7, 获取所有键或值
echo "${!my_dict[@]}"  # 输出所有键
echo "${my_dict[@]}"   # 输出所有值

# 8, 获取数组长度
echo "${#my_dict[@]}"  # 输出数组长度

# 9, 删除整个数组
unset my_dict

# 清空数组
my_dict=()

# 10, 读取文件内容到关联数组
while IFS='=' read -r key value; do
    my_dict["$key"]="$value"
done < file.txt

# 11, 嵌套结构模拟
declare -A person
person["name"]="Bob"
person["address"]="street=Main;city=Beijing"

IFS=';' read -ra addr <<< "${person["address"]}"
for item in "${addr[@]}"; do
    echo "$item"
done

# 12, 单词频率统计
declare -A word_count

while IFS= read -r line; do
    for word in $line; do
        ((word_count[$word]++))
    done
done < file.txt

for word in "${!word_count[@]}"; do
    echo "$word: ${word_count[$word]}"
done

# 13, 字符串替换
for key in "${!my_dict[@]}"; do
    my_dict["$key"]="new_${my_dict[$key]}"
done

# 14, 数组切片
keys=("${!my_dict[@]}")
for ((i=0; i<${#keys[@]}; i+=2)); do
    echo "${keys[$i]}: ${my_dict[${keys[$i]}]}"
done

# 15, 数组排序
keys=("${!my_dict[@]}")
IFS=$'\n' sorted_keys=($(sort <<<"${keys[*]}"))
for key in "${sorted_keys[@]}"; do
    echo "$key: ${my_dict[$key]}"
done

# 16, 配置文件解析
declare -A config
config["host"]="example.com"
config["port"]="8080"

echo "连接 ${config["host"]}:${config["port"]}"

