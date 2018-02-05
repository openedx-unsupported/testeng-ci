pipeline {
    agent { label 'master' }
    stages {
        stage('test') {
            steps {
                checkout([$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[url: 'https://github.com/edx/testeng-ci']]])
	    }
        }
        stage('phony') {
            steps {
                sh 'cd testeng-ci'
            }
        }
    }
}
