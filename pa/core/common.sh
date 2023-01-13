err_exit() {
    echo $1 | $TO
    echo "Please contact support for further assistance." | $TO
    echo "Install log is located at $LOG_FILE and install_log directory(if partial success)" 
    echo "Exiting..." | $TO
    exit 1;
} 




