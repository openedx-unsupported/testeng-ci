# process_webhooks

Process webhooks and either send them to the specified endpoint(s), or
store them in an SQS queue.

## Deploying the code

The s3 bucket must first exist.
To create one using the terraform from the edx-ops/terraform repo:
```
terraform plan --target aws_s3_bucket.edx-testeng-spigot
terraform apply --target aws_s3_bucket.edx-testeng-spigot
```

To zip and upload a new version, using the aws cli:
```
zip process_webhooks.zip process_webhooks.py constants.py
aws s3 cp process_webhooks.zip s3://edx-tools-spigot/
rm process_webhooks.zip
```
