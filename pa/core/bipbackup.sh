#!/bin/sh
 
source ./common_env.sh
source ./common.sh
source ./utils.sh

source $SYSCONFIG_FULLPATH



echo
echo
echo
echo
echo "********* Upgrade of BI Platform involves un-installing existing 1.0 version *********"
echo
echo
echo Following files and folders containing user data and configuration will be backed-up from the existing 1.0 installation before upgrade. The backed up user data and configuration will be automatically re-applied as part of upgrade.
echo "****NOTE: If changes have been made to any files or folder other than ones mentioned below. The changes will have to be re-applied manually. This also includes any data model files under schema-workbench folder."
echo "A copy of the BI Platform folder will be available under /tmp/<CURENT DATE>. List of files and folders that will be backed up:"
read -p "Press Enter to continue" dummy
echo
echo "$BIPLATFORM_HOME/administration-console/resource/config"
echo "All folders under <solution path> except system and admin"
echo "<solution path>/admin/resources/metadata"
echo "<solution path>/system/olap"
echo $BIPLATFORM_HOME/biserver-ce/tomcat/webapps/pentaho/WEB-INF/classes
echo $BIPLATFORM_HOME/biserver-ce/tomcat/conf/server.xml
echo $BIPLATFORM_HOME/biserver-ce/tomcat/webapps/pentaho/WEB-INF/web.xml
echo $BIPLATFORM_HOME/biserver-ce/tomcat/webapps/pentaho/META-INF/context.xml
echo "<solution path>/system/applicationContext-spring-security-hibernate.properties"
echo "<solution path>/system/hibernate/postgresql.hibernate.cfg.xml"
echo "<solution path>/system/data-access/settings.xml"

#Prompt to stop Upgrade
while true
do
   echo "Press N to exit. Press Y to continue"
   read STOP_UPGRADE
  case $STOP_UPGRADE in
     y|Y|yes|Yes|YES)
     break;
     ;;
     n|N|no|No|NO)
      echo "Exiting the upgrade process."
      exit 1
      ;;
       *)
     echo "You entered an invalid option. Please enter (Y/N)."
      ;;
    esac
done 

