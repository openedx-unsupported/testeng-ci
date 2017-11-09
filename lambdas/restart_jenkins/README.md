# jenkins_restart

Post to the safeRestart URL to restart the Jenkins application

## Deploying the code

The s3 bucket must first exist.
To create one using the terraform from the edx-ops/terraform repo:
```
terraform plan --target aws_s3_bucket.edx-tools-jenkins-restart
terraform apply --target aws_s3_bucket.edx-tools-jenkins-restart
```

To zip and upload a new version, using the aws cli:
```
zip restart_jenkins.zip restart_jenkins.py
aws s3 cp restart_jenkins.zip s3://edx-tools-jenkins-restart/
rm restart_jenkins.zip
```

To upload credentials to the credentials bucket:
```
aws s3 cp jenkins_safe_restart_credentials.json s3://edx-tools-credentials/
```
