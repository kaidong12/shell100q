

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
                    git status
                    virsh list --all
                    ping -c 5 10.0.99.15
                    grep -A 30 pm5: /home/tester/yaml/${params.YAML_PATH}/IPSEC_IKEV2.yaml
                    date
                    echo "============================environment============================"
                    
                    echo "----------------------------------------------------------------------------------------------------"
                    # /home/tester/vtest/bin/runner standard_ipsec_tier1 -ikev2 -v -ntr -ns -m ipsec_ikev2 -t setup -t P0 -t cleanup -q;
                    /home/tester/vtest/bin/runner standard_ipsec_tier1 -ikev2 -y /home/tester/yaml/${params.YAML_PATH}/IPSEC_IKEV2.yaml -v -ntr -ns -m ipsec_ikev2 -n tb -o -b next -t setup -t P0 -t cleanup -q;
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
