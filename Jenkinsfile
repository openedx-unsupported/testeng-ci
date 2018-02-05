pipeline {
    agent none
    stages {
        stage('test') {
            agent { label 'master' }
            steps {
                sh 'echo hi'
            }
        }
        stage('phony') {
            agent { label 'master' }
            steps {
                sh 'bash test.sh'
            }
        }
    }
}
