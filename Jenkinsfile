pipeline {
    agent none
    stages {
        stage('Run Tests') {
            parallel {
                stage('Test On Windows') {
                    agent {
                        label "master"
                    }
                    steps {
                        sh "echo hey"
			sh "sleep 60"
                    }
                }
                stage('Test On Linux') {
                    agent {
                        label "master"
                    }
                    steps {
                        sh "echo yo"
			sh "sleep 60"
                    }
                }
            }
        }
    }
}
