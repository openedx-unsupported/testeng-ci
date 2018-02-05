pipeline {
    agent none
    stages {
        stage('test') {
            agent { label 'master' }
            steps {
                sh 'bash test.sh'
            }
        }
        stage('phony') {
            agent { label 'master' }
            steps {
                sh 'sleep 60'
            }
        }
    }
}
