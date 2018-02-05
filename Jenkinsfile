pipeline {
    agent none
    stages {
        stage('test') {
            agent { label 'master' }
            steps {
                checkout([$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[url: 'https://github.com/edx/testeng-ci']]])
            stash testeng-ci
	    }
        }
        stage('phony') {
            agent { label 'master' }
            steps {
		unstash testeng-ci
                sh 'cd testeng-ci'
            }
        }
    }
}
