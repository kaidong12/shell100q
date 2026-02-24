#!/bin/bash

webex_id=`grep webex_id /home/tester/vtest/local.preference.yaml | grep -v '^#' | awk -F: '{print $2}'`
host_name=`hostname`
test=`ps -ef | grep vtest | grep -P 'testbed|run' | awk '{print $10}' | head -1`
# test="testing"
# echo $test

if [ -n "$test" ]; then
  /home/tester/bin/notify_bot "$webex_id" "Host Name: $host_name | Suite running: $test"

  #/home/tester/bin/notify_bot "kaidyan@cisco.com" "Test running: $test"
  #/home/tester/bin/notify_bot "kaidyancisco.com" "db_build_id: 4588876 | Test running: xxx | ------------- |   Test results summary:  | test running: enterprise_certs | start to run: enterprise_certs | stop run: ipsec_ikev2          |aaa:1 | bbb:2|ccc|fdfdasfa"
  #/home/tester/bin/notify_bot "kaidyan@cisco.com" "db_build_id: 4588876 | Test running: xxx | ------------- |   Test results summary:  | test running: enterprise_certs | start to run: enterprise_certs | stop run: ipsec_ikev2          |aaa:1 | bbb:2|ccc|fdfdasfa"
fi
