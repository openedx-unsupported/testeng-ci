pipeline {
    agent none
    stages {
        stage('Run Tests') {
            agent { label 'master' }
            steps {
                sh 'bash geroigr.sh'
            }
        }
	    stage('test') {
            agent { label 'master' }
            steps {
                sh 'echo hi'
            }
        }
    }
}
