# Webhook Processor

Processes webhooks by reading them from a kinesis stream and forwarding to Jenkins

## Deploying the code

The s3 bucket must first exist.
To create one using the terraform from the edx-ops/terraform repo:
terraform plan --target aws_s3_bucket.edx-testeng-lambda-webhook
terraform apply --target aws_s3_bucket.edx-testeng-lambda-webhook

To zip and upload a new version, using the aws cli:
```
zip webhook_processor.zip webhook_processor.py
aws s3 cp webhook_processor.zip s3://edx-testeng-lambda-webhook/
rm webhook_processor.zip
```

Now you need to update (and apply) the terraform for the lambda
so that it will use the new version.

Unfortunately finding the version number is not possbile via the aws cli,
only through the REST API, the SDKs, or the web console.

In the web console:
* Go to the s3 bucket web interface (https://console.aws.amazon.com/s3)
* Navigate to the bucket, and then the .zip file.
* Look for the "Version ID" on the Overview tab.

This is what you will put in the terraform.tfvars file.
  lambda2_version = "<the new version id>"

Note the target (jenkins) URL is also configured in the terraform.tfvars file.

## Troubleshooting

### Viewing data in the kinesis stream
You can use the aws-cli to troubleshoot the data that was
put on the stream like this:

SHARD_ITERATOR=$(aws kinesis get-shard-iterator \
   --shard-id shardId-000000000000 \
   --shard-iterator-type TRIM_HORIZON \
   --stream-name gh_webhooks \
   --query 'ShardIterator')
aws kinesis get-records --shard-iterator $SHARD_ITERATOR

You can then use that output to configure a test event, which you invoke
via the lambda console.

### Invoking the lambda function
$ aws lambda invoke \
--function-name CreateTableAddRecordsAndRead  \
--region us-east-1 \
--profile adminuser \
output.txt


$ aws lambda invoke \
--invocation-type RequestResponse \
--function-name helloworld \
--region us-east-1 \
--payload '{"key1":"value1", "key2":"value2", "key3":"value3"}' \
output.txt
