pipeline {
    agent none
    stages {
        stage('test') {
            agent { label 'master' }
            steps {
                checkout([$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[url: 'https://github.com/edx/testeng-ci']]])
            }
        }
        stage('phony') {
            agent { label 'master' }
            steps {
                sh 'cd testeng-ci'
            }
        }
    }
}
