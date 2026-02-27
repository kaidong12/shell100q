
pipeline {
    agent { label "${params.NODE_LABEL}" }

    stages {
        stage('Show selected parameters') {
            steps {
                echo "WEBEX_ROOM_NAME = ${params.WEBEX_ROOM_NAME}"
                echo "NODE_LABEL    = ${params.NODE_LABEL}"
                echo "YAML_PATH    = ${params.YAML_PATH}"
                echo "EXIT_ON_FAIL    = ${params.EXIT_ON_FAIL}"
            }
        }

        stage('Resolve Webex Room ID') {
            steps {
                script {
                    def roomMap = [
                        "auto regression": env.WEBEX_ROOM_ID_LANCE,
                        "sdwan automation": env.WEBEX_ROOM_ID_ALL
                    ]

                    def webexRoomId = roomMap[params.WEBEX_ROOM_NAME]

                    if (!webexRoomId) {
                        error "Invalid WEBEX_ROOM_NAME selection"
                    }

                    echo "Using Webex room ID: $webexRoomId"
                    env.WEBEX_ROOM_ID = webexRoomId
                }
            }
        }
        
        stage('Show parameters') {
            steps {
                echo "WEBEX_ROOM_ID = ${env.WEBEX_ROOM_ID}"
                echo "NODE_LABEL    = ${params.NODE_LABEL}"
                echo "YAML_PATH     = ${params.YAML_PATH}"
                echo "EXIT_ON_FAIL  = ${params.EXIT_ON_FAIL}"
            }
        }
        
        stage('Reset-1: reset_environment') {
            steps {
                script {
                    build job: 'reset_environment',
                          propagate: params.EXIT_ON_FAIL,
                          parameters: [
                              string(name: 'WEBEX_ROOM_ID', value: env.WEBEX_ROOM_ID),
                              string(name: 'NODE_LABEL', value: params.NODE_LABEL),
                              string(name: 'YAML_PATH', value: params.YAML_PATH)
                          ]
                }
            }
        }

        stage('Test-1: cExpressv4v6_DUAL_bgp_ipv4_ipv6') {
            steps {
                script {
                    build job: 'cExpressv4v6_DUAL_bgp_ipv4_ipv6',
                          propagate: params.EXIT_ON_FAIL,
                          parameters: [
                              string(name: 'WEBEX_ROOM_ID', value: env.WEBEX_ROOM_ID),
                              string(name: 'NODE_LABEL', value: params.NODE_LABEL),
                              string(name: 'YAML_PATH', value: params.YAML_PATH)
                          ]
                }
            }
        }

        stage('Reset-2: reset_environment') {
            steps {
                script {
                    build job: 'reset_environment',
                          propagate: params.EXIT_ON_FAIL,
                          parameters: [
                              string(name: 'WEBEX_ROOM_ID', value: env.WEBEX_ROOM_ID),
                              string(name: 'NODE_LABEL', value: params.NODE_LABEL),
                              string(name: 'YAML_PATH', value: params.YAML_PATH)
                          ]
                }
            }
        }

        stage('Test-2: cExpress_IPv6-transport_service') {
            steps {
                script {
                    build job: 'cExpress_IPv6-transport_service',
                          propagate: params.EXIT_ON_FAIL,
                          parameters: [
                              string(name: 'WEBEX_ROOM_ID', value: env.WEBEX_ROOM_ID),
                              string(name: 'NODE_LABEL', value: params.NODE_LABEL),
                              string(name: 'YAML_PATH', value: params.YAML_PATH)
                          ]
                }
            }
        }

        stage('Reset-3: reset_environment') {
            steps {
                script {
                    build job: 'reset_environment',
                          propagate: params.EXIT_ON_FAIL,
                          parameters: [
                              string(name: 'WEBEX_ROOM_ID', value: env.WEBEX_ROOM_ID),
                              string(name: 'NODE_LABEL', value: params.NODE_LABEL),
                              string(name: 'YAML_PATH', value: params.YAML_PATH)
                          ]
                }
            }
        }

        stage('Test-3: CEXPRESS_GRE') {
            steps {
                script {
                    build job: 'CEXPRESS_GRE',
                          propagate: params.EXIT_ON_FAIL,
                          parameters: [
                              string(name: 'WEBEX_ROOM_ID', value: env.WEBEX_ROOM_ID),
                              string(name: 'NODE_LABEL', value: params.NODE_LABEL),
                              string(name: 'YAML_PATH', value: params.YAML_PATH)
                          ]
                }
            }
        }

        stage('Reset-4: reset_environment') {
            steps {
                script {
                    build job: 'reset_environment',
                          propagate: params.EXIT_ON_FAIL,
                          parameters: [
                              string(name: 'WEBEX_ROOM_ID', value: env.WEBEX_ROOM_ID),
                              string(name: 'NODE_LABEL', value: params.NODE_LABEL),
                              string(name: 'YAML_PATH', value: params.YAML_PATH)
                          ]
                }
            }
        }

        stage('Test-4: cEdgeBFD') {
            steps {
                script {
                    build job: 'cEdgeBFD',
                          propagate: params.EXIT_ON_FAIL,
                          parameters: [
                              string(name: 'WEBEX_ROOM_ID', value: env.WEBEX_ROOM_ID),
                              string(name: 'NODE_LABEL', value: params.NODE_LABEL),
                              string(name: 'YAML_PATH', value: params.YAML_PATH)
                          ]
                }
            }
        }

        // stage('Reset-5: reset_environment') {
        //     steps {
        //         script {
        //             build job: 'reset_environment',
        //                   propagate: params.EXIT_ON_FAIL,
        //                   parameters: [
        //                       string(name: 'WEBEX_ROOM_ID', value: env.WEBEX_ROOM_ID),
        //                       string(name: 'NODE_LABEL', value: params.NODE_LABEL),
        //                       string(name: 'YAML_PATH', value: params.YAML_PATH)
        //                   ]
        //         }
        //     }
        // }

    }

    post {
        always {
            echo "Pipeline finished. All jobs were triggered regardless of failures."
        }
    }
}

