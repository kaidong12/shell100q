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
                    pwd
                    cd /home/tester/kaidyan/scripts
                    ./poll_run_status.sh
                    ps -ef | grep vtest | grep -P 'testbed|run' | awk '{print \$2}'
                    ps -ef | grep vtest | grep -P 'testbed|run' | awk '{print \$2}' | xargs -r kill -9

                    sleep 5m

                    echo "delete /home/tester/testbeds/tb"
                    rm -rf /home/tester/testbeds/tb
                    
                    echo "============================environment============================"
                    echo $PATH
                    python -V
                    echo "============================environment============================"

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
