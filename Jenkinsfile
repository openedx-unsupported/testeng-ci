pipeline {
    agent { label 'master' }
    stages {
        stage('test') {
            steps {
	        checkout changelog: false, poll: false, scm: [$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [[$class: 'RelativeTargetDirectory', relativeTargetDir: 'testeng-ci']], submoduleCfg: [], userRemoteConfigs: [[url: 'https://github.com/edx/testeng-ci.git']]]
            }
        }
        stage('phony') {
            steps {
                sh 'cd testeng-ci'
            }
        }
    }
}
