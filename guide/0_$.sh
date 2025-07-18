#demo the usage of $ in bash

$ 是一个核心符号，主要用于 变量扩展 和 特殊功能引用。在 Bash 中，$ 符号有多种用法，以下是一些常见的用法：

1. 变量扩展：$ 符号用于获取变量的值。例如，如果变量 var 的值为 "hello"，则 $var 将返回 "hello"。
2. 获取变量值：${variable} 可以用于获取变量的值。例如，${var} 将返回变量 var 的值。
3. 获取数组元素：${array[index]} 可以用于获取数组的元素。例如，${arr[0]} 将返回数组 arr 的第一个元素。
4. 获取数组长度：${#array[@]} 可以用于获取数组的长度。例如，${#arr[@]} 将返回数组 arr 的长度。

5. 特殊功能引用：$ 符号还可以用于引用特殊功能，如命令替换、算术运算等。
6. 获取命令的输出：$(command) 可以用于执行命令并获取其输出。例如，$(pwd) 将返回当前工作目录的路径。
7. 算术运算：$((expression)) 可以用于执行算术运算，并将结果返回。例如，$((1+2)) 将返回 3。

8. 获取字符串长度：${#string} 可以用于获取字符串的长度。例如，${#str} 将返回字符串 str 的长度。
9. 获取子字符串：${string:offset:length} 可以用于获取字符串的子字符串。例如，${str:2:4} 将返回字符串 str 从第 3 个字符开始的 4 个字符。

10. 获取命令的退出状态：$? 可以用于获取上一个命令的退出状态。例如，如果上一个命令成功执行，则 $? 将返回 0；如果上一个命令失败，则 $? 将返回非零值。
11. 获取当前进程的 PID：$$ 可以用于获取当前进程的 PID。例如，$$ 将返回当前进程的 PID。

12. 获取当前用户的用户名：$USER 可以用于获取当前用户的用户名。例如，$USER 将返回当前用户的用户名。
13. 获取当前 shell 的版本：$BASH_VERSION 可以用于获取当前 shell 的版本。例如，$BASH_VERSION 将返回当前 shell 的版本号。
14. 获取当前 shell 的 PID：$PPID 可以用于获取当前 shell 的 PID。例如，$PPID 将返回当前 shell 的 PID。

