pipeline {
    agent none
    stages {
        stage('Run Tests') {
            agent { label 'master' }
            sh 'bash geroigr.sh'
        }
	    stage('test') {
            agent { label 'master' }
	        sh 'echo hi'
        }
    }
}
