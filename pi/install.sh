#!/bin/bash
LOGFILE=./install.log
exec > >(tee -a $LOGFILE) 2>&1
set -e
# Exit directly if a command exits with a non-zero status.
version="Raptor v2.20.7"
DEBIAN_VERSION=`lsb_release -a | grep Release | awk '{print $2}'`
choice=$1
skip=$2
sw_env=$3

# Source code path under RaptorBundle
sysDeps="./sys-deb"
pythonDeps="./pip-whl"
system_configs_path="./configs"
raptorPath="./python_service/raptor"
ui_service="./extend/ui_service/dist-pro"
doc_service="./extend/doc_service/dist"
golang_service="./extend/golang_service"
golang_service_conf="./extend/golang_service/config/"
debugScriptsPath="./scripts"

# System services path on raptor box
sysServicePath="/etc/systemd/system"
serials_db_path="/etc/raptor.conf/db"

# Raptor installation path on raptor box
raptor_home="/home/pi/raptorbox"
ui_service_path="$raptor_home/ui_service"
doc_service_path="$raptor_home/doc_service"
golang_service_path="$raptor_home/golang_service"
raptor_path="$raptor_home/raptor"
raptor_configs_path="$raptor_path/configs"
robot_report_path="/home/pi/raptorbox/reports"
robot_screenshot_path="$robot_report_path/screenshot"
robot_output_path="$robot_report_path/xml-output"
debug_path="/home/pi/debug"

# Raptor configuration path
etc_config_path="/etc/raptor.conf/"
nginx_config_path="$etc_config_path/config"
service_config_file="$raptor_configs_path/config.ini"
nginx_install_path="/etc/nginx"

# Raptor log path
logPath="$raptor_home/logs"
systemLogPath="$raptor_home/logs/system"
outputLog="$raptor_home/logs/system/raptorbox.service.log"
errorLog="$raptor_home/logs/system/raptorbox.error.log"

# Robot resource
robot_folder_path="./robot_resource"
robot_exe_path="/home/pi"


function log(){
  echo -e "\033[34;49;1m--------------------------- $1 ---------------------------\033[39;49;0m"
}

function setSysService(){
  for service_file in "$sysServicePath"/raptorbox_*.service; do
      service_name=$(basename "$service_file")

      if [ -n "$service_name" ]; then
        echo "$1 Service: $service_name"
        sudo systemctl "$1" "$service_name" || true
        # shellcheck disable=SC2181
        if [ $? -eq 0 ]; then
          echo "Successful $1 the service."
        else
          echo "Failed to $1 service."
        fi
      else
        echo "No service were found."
      fi
  done
  sleep 5
}

function chkPathExist(){
  echo "$1"
  if [ ! -d "$1" ]; then
    # shellcheck disable=SC2086
    echo $1
    mkdir -p "$1"
  fi
}

log "Configure CAN-FD/CAN"
if [ $DEBIAN_VERSION -eq 12 ]; then
  destConfigPath="/boot/firmware"
elif [ $DEBIAN_VERSION -eq 11 ]; then
  destConfigPath="/boot"
else 
  echo "The Debian version is not supportted: $DEBIAN_VERSION" 
  exit 1
fi

if [ "$choice" = "can" ] || [ "$choice" = "CAN" ] || [ "$choice" = "Can" ]; then
  sudo cp "$system_configs_path"/config-can.txt "$destConfigPath"/config.txt
  log "Configure CAN board"
else
  sudo cp "$system_configs_path"/config-canfd.txt "$destConfigPath"/config.txt
  log "Configure CAN-FD board"
fi

# Enable CAN  interface when system is on
sudo cp "$system_configs_path"/interfaces /etc/network/interfaces
sudo cp "$system_configs_path"/sysctl.conf /etc/sysctl.conf
sudo cp "$system_configs_path"/can.rules /etc/udev/rules.d/80-can.rules
log "Configure CAN-FD/CAN END"

log "Check Path"
chkPathExist "$raptor_path"
chkPathExist "$raptor_configs_path"
chkPathExist "$logPath"
chkPathExist "$systemLogPath"
chkPathExist "$ui_service_path"
chkPathExist "$doc_service_path"
chkPathExist "$golang_service_path"
chkPathExist "$etc_config_path"
chkPathExist "$serials_db_path"
chkPathExist "$debug_path"
chkPathExist "$robot_report_path"
chkPathExist "$robot_screenshot_path"
chkPathExist "$robot_output_path"

touch $outputLog
touch $errorLog
log "Check Path END"

log "Check and copy the robot_resource folder to user home"
if [ -d "$robot_folder_path" ]; then
  sudo cp -r $robot_folder_path $robot_exe_path
  sudo rm -rf $robot_folder_path
else
  log "There's no 'robot_resource' folder included in raptor bundle"
fi
log "Check and copy the robot_resource folder to user home END"

log "Backup the configs for service"
backup_configs_path="$raptor_configs_path.backup"
files=$(ls -A $raptor_configs_path)
if [ -z "$files" ]; then
  log "INI files does not exist"
  chkPathExist $backup_configs_path
else
  sudo cp "$raptor_configs_path"/* $backup_configs_path
  log "INI files backup to $backup_configs_path"
fi
log "Backup the configs for service END"

if [ "$skip" = "skip" ]; then
    log "Skipping library installation"
else
	log "Configure System Lib and Python Lib"
	log "wireshark-common wireshark-common/install-setuid boolean true" | sudo debconf-set-selections

  if [ $DEBIAN_VERSION -eq 11 ]; then
  	log "Configure System Lib and Python Lib for Debian 11 (bullseye)"
    for deb_file in "$sysDeps"/*.deb
    do
        sudo DEBIAN_FRONTEND=noninteractive dpkg -i -E -G "$deb_file"
    done

    log "Upgrade Real Pip with Standalone Pip"
    sudo python ./pip.pyz install --ignore-installed  "$pythonDeps"/pip-23.1-py3-none-any.whl --no-index --find-link "$pythonDeps" || exit 1
    log "Upgrade Real Pip with Standalone Pip END"

    sudo pip3 install --ignore-installed -r "$pythonDeps"/requirements.txt --no-index --find-links "$pythonDeps"/ || exit 1
    log "Configure System Lib and Python Lib END"
  elif [ $DEBIAN_VERSION -eq 12 ]; then
  	log "Configure System Lib and Python Lib for Debian 12 (bookworm)"
  	sudo sudo DEBIAN_FRONTEND=noninteractive dpkg -i -E -G "$sysDeps-12"/*.deb
    sudo pip3 install --break-system-packages --ignore-installed -r "$pythonDeps-12"/requirements.txt --no-index --find-links "$pythonDeps-12"/ || exit 1
    log "Configure System Lib and Python Lib END"
  else 
    echo "The Debian version is not supportted: $DEBIAN_VERSION" 
    exit 1
  fi
fi

log "Stop the deprecated services"
if [ -e "/etc/systemd/system/raptorbox_uart.service" ]; then
    log "remove the deprecated service uart."
    sudo systemctl stop raptorbox_uart.service || true
    sudo systemctl disable raptorbox_uart.service || true
    sudo rm -rf /etc/systemd/system/raptorbox_uart.service || true
fi

sleep 1
log "Stop the deprecated services END"

log "Unzip python services"
sudo cp -r "$raptorPath"/* "$raptor_path"/
sleep 1
log "Unzip python services END"

log "Stop the Services"
setSysService stop
log "Stop the Services END"

log "Install Golang Service"
sudo cp -r "$golang_service_conf" "$etc_config_path"
sudo cp -r "$golang_service"/* "$golang_service_path" || true
log "Install Golang Service END"

log "Install Doc Service"
if [ -e "$doc_service_path" ]; then
  sudo rm -rf "$doc_service_path"/*
fi
sudo cp -r "$doc_service"/* "$doc_service_path"/
log "Install Doc Service END"

log "Install Frontend"
if [ -e "$ui_service_path" ]; then
  sudo rm -rf "$ui_service_path"/*
fi
sudo cp -r "$ui_service"/* "$ui_service_path"/
sudo cp "$nginx_config_path"/nginx.conf "$nginx_install_path"/nginx.conf
log "Install Frontend END"

log "Upload the static page of upgrade log"
sudo cp "$nginx_config_path"/upgradelog.html "$logPath"/upgradelog.html
log "Upload the static page of upgrade log END"

if [ -f "$service_config_file" ]; then
  log "service config ini file exist"
else
  log "service config ini file does not exist"
fi

if [ "$sw_env" = "dev" ]; then
  sed -i "s|^\(sw_env *= *\).*|\1$sw_env|" "$service_config_file"
  version="$version (dev)"
  log "Parameter sw_env updated successfully."
else
  log "Parameter sw_env not found in the INI file."
fi

if grep -q "sw_version" "$service_config_file"; then
  sed -i "s|^\(sw_version *= *\).*|\1$version|" "$service_config_file"
  log "Parameter sw_version updated successfully."
else
  log "Parameter sw_version not found in the INI file."
fi

log "Resume local.ini file for service"
if [ -f "$raptor_configs_path.backup/local.ini" ]; then
  sudo cp $raptor_configs_path.backup/local.ini $raptor_configs_path/local.ini
  log "local.ini file recovered"
else
  log "backup local.ini file does not exist"
fi
log "Resume local.ini file for service END"

log "Write cantype to local.ini"
if [ "$choice" = "canfd" ] || [ "$choice" = "CANFD" ] || [ "$choice" = "CanFD" ] || [ "$choice" = "can-fd" ]; then
  sed -i 's/= can$/= canfd/g' $raptor_configs_path/local.ini
  log "Change cantype to canfd"
else
  sed -i 's/= canfd$/= can/g' $raptor_configs_path/local.ini
  log "Change cantype to can"
fi
log "Write cantype to local.ini END"

log "Converting ini files to Unix format"
if [ -d "$raptor_configs_path" ]; then
  sudo dos2unix "$raptor_configs_path"/*.ini
  log "INI files converted"
else
  log "service configs path does not exist"
fi
log "Converting ini files to Unix format END"

log "Copy config-can.txt and config-canfd.txt to configs"
if [ -d "$raptor_configs_path" ]; then
  sudo cp "$system_configs_path"/config-canfd.txt "$raptor_configs_path"/config-canfd.txt
  sudo cp "$system_configs_path"/config-can.txt "$raptor_configs_path"/config-can.txt
else
  log "service configs path does not exist"
fi
log "Copy config-can.txt and config-canfd.txt to configs END"

log "Modifying file permissions"
# shellcheck disable=SC2231
for golang_service in $golang_service_path/*; do
  sudo chmod +x "$golang_service"
done
if [ "$sw_env" = "dev" ]; then
  sudo chown pi:pi -R $raptor_path
  log "Change owner and group of /home/pi/raptorbox/raptor to pi:pi in dev mode"
else
  log "Not in dev mode."
fi
log "Modifying file permissions END"

log "Disable the services"
setSysService disable

log "Configure Auto-start"
# shellcheck disable=SC2231
for service_config in $system_configs_path/*.service; do
  sudo cp "$service_config" "$sysServicePath"/
done

log "Daemon reloading"
sudo systemctl daemon-reload

log "Enable the services"
setSysService enable

log "Disable the apache2 service"
sudo systemctl stop apache2 || true
sudo systemctl disable apache2 || true

log "Configure Auto-start END"


log "Install the debug scripts"
cp $debugScriptsPath/* $debug_path/
sudo chown pi:pi $debug_path/*.sh
sudo chmod 755 $debug_path/*.sh
cp $debugScriptsPath/.bash_aliases /home/pi/
dos2unix $debug_path/*
dos2unix /home/pi/.bash_aliases
source /home/pi/.bash_aliases
log "Install the debug scripts END"

log "Configure NetWorkManager"
if [ $DEBIAN_VERSION -eq 11 ]; then
  systemctl disable dhcpcd
  systemctl enable NetworkManager
fi

log "Install Successfully"
log "System Will Reboot in 3 Seconds"
log "Raptor system upgrade done, please go back to the system config page to check the Raptor system version."
sleep 3
sudo reboot
