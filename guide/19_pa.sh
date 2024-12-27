#!/bin/bash

export LOG_FILE="/tmp/pa_install.log"
export TO="tee -a  ${LOG_FILE}"
export LINUX_RELEASE=`cat ${LINUX_RELEASE_FILE}`
export RHEL6="Red Hat.* Linux.*6\..*"
export IDB_SERVER="true"

function err_exit() {
    echo $1 | $TO
    echo "Please contact support for further assistance." | $TO
    echo "Install log is located at $LOG_FILE and install_log directory(if partial success)" 
    echo "Exiting..." | $TO
    exit 1;
} 

if [[ ! $LINUX_RELEASE =~ $RHEL6 ]]; then
    err_exit "RHEL5 not supported yet"
fi

if [ "$IDB_SERVER" = "true" ]
then
echo "Setup Server DB" | $TO
./configDB.sh
if [ $? -ne 0 ]; then
    exit 1
fi


if [ "" = "$PA_HOME" ] ; then
   source /etc/sysconfig/primeanalytics/primea
fi
function install_bin() {
    cp -rf bin $PA_HOME
    tar -C $PA_HOME/bin/backup_restore -zxvf $INSTALL_DIR_CORE/../pentaho/backup_restore-*.tar.gz >/dev/null
    pushd $PA_HOME/bin/backup_restore  >/dev/null
    if [ "$INSTALL_TYPE" = "all" ] || [ "$INSTALL_TYPE" = "bip" ]; then
        chmod u+x BIPlatform/*.sh
        # chmod命令通过修改文件系统中的权限位来改变文件或目录的权限。
        # 权限位分为三类：读（r）、写（w）和执行（x），
        # 每类权限又分为三类用户：文件所有者（u）、所属组（g）和其他用户（o）。
        # u+x表示为文件所有者增加执行权限。
        chown -R bipuser BIPlatform
        cp -f $INSTALL_DIR_CORE/../pentaho/bi_pwd_update.sh ../
        cp -f $INSTALL_DIR_CORE/../pentaho/bip-change-password.jar ../
    fi
    if [ "$INSTALL_TYPE" = "all" ] || [ "$INSTALL_TYPE" = "db" ]; then
        chmod u+x Database/*.sh
        chown -R primea Database
    fi
    popd  >/dev/null
}

export TRUVISO_IP="localhost"
export PGPORT=5432
export DB_USER=$PA_USER
TRUCQ_CONNECT_STRING="-h $TRUVISO_IP -p $PGPORT -U $DB_USER"
psql  $TRUCQ_CONNECT_STRING < mkschema.sql >>$LOG_FILE 2>&1
if [ $? -ne 0 ]; then
    err_exit "Fatal error executing mkschema.sql"
fi

# psql 是一个用于与PostgreSQL数据库交互的命令行工具。
# $TRUCQ_CONNECT_STRING 是一个环境变量，包含了连接到数据库所需的连接字符串，例如用户名、数据库名、主机名等。
# < mkschema.sql 表示将mkschema.sql文件的内容作为输入传递给psql命令。
# >>$LOG_FILE 表示将psql命令的输出追加到$LOG_FILE指定的日志文件中。
# 2>&1 表示将标准错误（2）重定向到标准输出（1），这样所有的输出（包括错误信息）都会被记录到日志文件中。

sync; echo 3 > /proc/sys/vm/drop_caches
echo "DB Host: $TRUVISO_IP, DB Port: $PGPORT, DB User: $DB_USER" | $TO
echo "Install Successfully Completed `date`" | $TO

# 这段Shell命令主要用于清空Linux系统中的页面缓存、目录项缓存和inode缓存。下面是对这段命令的详细解释：
# sync 命令：这个命令的作用是确保所有待写入的数据都被写入磁盘。
# 在执行清空缓存的操作之前，先调用 sync 命令可以确保所有在内存中的数据都被写入到磁盘中，避免数据丢失。
# 
# echo 3 > /proc/sys/vm/drop_caches 命令：这个命令通过修改 /proc/sys/vm/drop_caches 文件来清空缓存。
# /proc/sys/vm/drop_caches 文件是一个虚拟文件，用于控制内核的缓存管理。通过向这个文件写入不同的数字，可以控制内核清空不同类型的缓存：
#     写入 1：清空页面缓存（Page cache）。
#     写入 2：清空目录项缓存（Dentry cache）。
#     写入 3：清空页面缓存、目录项缓存和inode缓存。
# 在这个命令中，写入 3 表示清空所有类型的缓存。

