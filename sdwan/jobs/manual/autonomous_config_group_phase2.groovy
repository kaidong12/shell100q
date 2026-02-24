

pipeline {
    agent {
        label params.NODE_LABEL
    }
    
    parameters {
        string(name: 'WEBEX_ROOM_ID', defaultValue: '', description: '')
        string(name: 'NODE_LABEL', defaultValue: '', description: '')
        string(name: 'YAML_PATH', defaultValue: '', description: '')
    }

    stages {
        stage('start') {
            steps {
                    sh """

                        curl -s -X POST "https://webexapis.com/v1/messages" \\
                          -H "Authorization: Bearer ${env.BOT_TOKEN}" \\
                          -H "Content-Type: application/json" \\
                          -d '{
                            "roomId": "${env.WEBEX_ROOM_ID}",
                            "text": "Jenkins job ${env.JOB_NAME} #${env.BUILD_NUMBER} on ${env.NODE_NAME} start!\\nBuild: ${env.BUILD_URL}"
                          }'
                    """
            }
        }
        stage('Execute') {
            steps {
                echo "Job           : ${env.JOB_NAME}"
                echo "Build number  : ${env.BUILD_NUMBER}"
                echo "Node          : ${env.NODE_NAME}"
                echo "Webex Room ID : ${params.WEBEX_ROOM_ID}"
                echo "YAML Path     : ${params.YAML_PATH}"
                sh """
                
                    echo "============================environment============================"
                    pwd
                    echo $PATH
                    python -V
                    cd /home/tester/vtest
                    pwd
                    git branch
                    git checkout p3
                    git status
                    virsh list --all
                    ping -c 5 10.0.99.15
                    grep -A 30 pm5: /home/tester/yaml/${params.YAML_PATH}/autonomous_1714_dmvpn_lite.yaml
                    date
                    echo "============================environment============================"
                    
                    echo "----------------------------------------------------------------------------------------------------"
                    source ~/.p3/bin/activate
                    python -V
                    # runsuite autonomous_config_group_phase2 -a 190 -w 300 -t setup -t rt -t cleanup -et test_service_vrf_and_interfaces_parcels;
                    runsuite autonomous_config_group_phase2 -y /home/tester/yaml/${params.YAML_PATH}/autonomous_1714_dmvpn_lite.yaml -n tb -o -b 26.1 -a 190 -w 300 -t setup -t rt -t cleanup -et test_service_vrf_and_interfaces_parcels;
                    echo "----------------------------------------------------------------------------------------------------"
                    date
                    
                """
            }
        }
        stage('end') {
            steps {
                    sh """
                        curl -s -X POST "https://webexapis.com/v1/messages" \\
                          -H "Authorization: Bearer ${env.BOT_TOKEN}" \\
                          -H "Content-Type: application/json" \\
                          -d '{
                            "roomId": "${env.WEBEX_ROOM_ID}",
                            "text": "Jenkins job ${env.JOB_NAME} #${env.BUILD_NUMBER} on ${env.NODE_NAME} end!\\nBuild: ${env.BUILD_URL}"
                          }'
                    """
            }
        }
    }
}
