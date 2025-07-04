#!/bin/bash
#if statement test

:<<EOF
# 1, 文件状态测试
###########################
# -d  目录
# -f  正规文件
# -r  可读
# -w  可写
# -x  可执行
# -s  文件长度大于0, 非空
# -e  文件是否存在
EOF

if [ -w test.log ]; then
  echo "文件可写
else
  echo "文件不可写
fi

:<<EOF
# 2, 字符串测试
###########################
# = 两个字符串相等
# != 两个字符串不相等
# -z 空字符串
# -n 非空字符串
EOF

echo -n "pleas enter you name:"
read NAME
if [ "$NAME" != "" ]; then
  echo "your name is: $NAME"
else
  echo "your didn't input a word!"
fi

nsname=$(ip netns list | grep ns1)
if [ -z "$nsname" ]; then
  log "namespace ns1 does not exist"
  sudo ip netns add ns1
fi

:<<EOF
# 3, 数值测试
###########################
# -eq 数值相等
# -ne 数值不相等
# -gt 大于
# -lt 小于
# -le 小于等于
# -ge 大于等于
EOF

NUMBER=111
if [ $NUMBER -gt 100 ]; then
    echo "大于100"
fi

:<<EOF
# 4, 组合测试
###########################
# -a 逻辑与
# -o 逻辑或
# !  逻辑否
EOF

NUMBER=99
if [ $NUMBER -lt 100 -a $NUMBER -gt 0 ]; then
    echo "分数合法"
fi

