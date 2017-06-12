# send_from_queue

Remove webhooks from the SQS queue and forward them back through the API Gateway.

## Deploying the code

The s3 bucket must first exist.
To create one using the terraform from the edx-ops/terraform repo:
```
terraform plan --target aws_s3_bucket.edx-testeng-spigot
terraform apply --target aws_s3_bucket.edx-testeng-spigot
```

To zip and upload a new version, using the aws cli:
```
zip send_from_queue.zip send_from_queue.py
aws s3 cp send_from_queue.zip s3://edx-tools-spigot/
rm send_from_queue.zip
```
