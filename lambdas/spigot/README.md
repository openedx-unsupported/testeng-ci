# Spigot

Processes webhooks and either sends them to the specified endpoint(s), or
stores them in an SQS stream.

## Deploying the code

The s3 bucket must first exist.
To create one using the terraform from the edx-ops/terraform repo:
terraform plan --target aws_s3_bucket.edx-testeng-spigot
terraform apply --target aws_s3_bucket.edx-testeng-spigot

To zip and upload a new version, using the aws cli:
```
zip spigot.zip spigot.py
aws s3 cp spigot.zip s3://edx-tools-spigot/
rm spigot.zip
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
