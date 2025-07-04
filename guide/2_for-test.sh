#!/bin/bash
#for statement test

set -x
for loop in what is you selections?
do
  echo $loop
done

set +x


string="what is your selections?"

for word in $string
do
  # echo $word
  echo ${#word}
  if [ ${#word} -gt 6 ]; then
    echo $word
  fi
done

for w in $string
do
  if ((${#w}>6)); then
  echo $w
  
  fi
done

for i in {0..100}  
do  
  if [ $((i % 3)) -eq 0 ]  
  then  
      echo $i  
  fi  
done

# Bash 的算术扩展 $(( )) 
# 在 Bash 中，$(( )) 是 算术扩展（Arithmetic Expansion）的语法
# 而其中的 $ 符号起到了 触发算术计算并返回结果 的关键作用。

for ((j=21; j <= 30; j++))
do
  echo $(( j % 3 ))   # 取余运算, $不能少
  if (( j % 3 == 0)); then
      echo $j
  fi
done

# 打印九九乘法表
for ((i=1;i<=9;i++))
do
  for ((j=1;j<=$i;j++))
  do
    printf "%d x %d = %-2d  " $j $i $((i*j))
  done
  echo
done
