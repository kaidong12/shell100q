
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

        stage('Test-1: sdwan_ssr_express_hw') {
            steps {
                script {
                    build job: 'sdwan_ssr_express_hw',
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

        stage('Test-2: bgp_vrrp_cedge') {
            steps {
                script {
                    build job: 'bgp_vrrp_cedge',
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

        stage('Test-3: cExpress_IPv6-transport_service') {
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

        stage('Test-4: cExpress_bgp_vEdge') {
            steps {
                script {
                    build job: 'cExpress_bgp_vEdge',
                          propagate: params.EXIT_ON_FAIL,
                          parameters: [
                              string(name: 'WEBEX_ROOM_ID', value: env.WEBEX_ROOM_ID),
                              string(name: 'NODE_LABEL', value: params.NODE_LABEL),
                              string(name: 'YAML_PATH', value: params.YAML_PATH)
                          ]
                }
            }
        }

        stage('Reset-5: reset_environment') {
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

        stage('Test-5: CEXPRESS_GRE') {
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

        stage('Reset-6: reset_environment') {
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
        
        stage('Test-6: ntp') {
            steps {
                script {
                    build job: 'ntp',
                          propagate: params.EXIT_ON_FAIL,
                          parameters: [
                              string(name: 'WEBEX_ROOM_ID', value: env.WEBEX_ROOM_ID),
                              string(name: 'NODE_LABEL', value: params.NODE_LABEL),
                              string(name: 'YAML_PATH', value: params.YAML_PATH)
                          ]
                }
            }
        }

        stage('Reset-7: reset_environment') {
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
        
        stage('Test-7: ospf_cedge') {
            steps {
                script {
                    build job: 'ospf_cedge',
                          propagate: params.EXIT_ON_FAIL,
                          parameters: [
                              string(name: 'WEBEX_ROOM_ID', value: env.WEBEX_ROOM_ID),
                              string(name: 'NODE_LABEL', value: params.NODE_LABEL),
                              string(name: 'YAML_PATH', value: params.YAML_PATH)
                          ]
                }
            }
        }

        stage('Reset-8: reset_environment') {
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
        
        stage('Test-8: cEdgeFNF') {
            steps {
                script {
                    build job: 'cEdgeFNF',
                          propagate: params.EXIT_ON_FAIL,
                          parameters: [
                              string(name: 'WEBEX_ROOM_ID', value: env.WEBEX_ROOM_ID),
                              string(name: 'NODE_LABEL', value: params.NODE_LABEL),
                              string(name: 'YAML_PATH', value: params.YAML_PATH)
                          ]
                }
            }
        }

        stage('Reset-9: reset_environment') {
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
        
        stage('Test-9: cedge_syslog') {
            steps {
                script {
                    build job: 'cedge_syslog',
                          propagate: params.EXIT_ON_FAIL,
                          parameters: [
                              string(name: 'WEBEX_ROOM_ID', value: env.WEBEX_ROOM_ID),
                              string(name: 'NODE_LABEL', value: params.NODE_LABEL),
                              string(name: 'YAML_PATH', value: params.YAML_PATH)
                          ]
                }
            }
        }

        stage('Reset-10: reset_environment') {
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
        
        stage('Test-10: cEdgeNat') {
            steps {
                script {
                    build job: 'cEdgeNat',
                          propagate: params.EXIT_ON_FAIL,
                          parameters: [
                              string(name: 'WEBEX_ROOM_ID', value: env.WEBEX_ROOM_ID),
                              string(name: 'NODE_LABEL', value: params.NODE_LABEL),
                              string(name: 'YAML_PATH', value: params.YAML_PATH)
                          ]
                }
            }
        }

        // stage('Reset-11: reset_environment') {
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

