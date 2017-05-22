# Webhook Forwarder

Forwards webhooks from the API Gateway to a Kinesis stream.

This is part of the Jenkins Webhook Interceptor plan, to queue and
manage webhooks triggered via Github activity for use in our CI systems.
The webhooks that this lambda function forwards are later consumed by
the 'webhook-processor' lambda, which will direct them to the appropriate
Jenkins instance

To zip and upload a new version, using the aws cli:
```
zip webhook_forwarder.zip webhook_forwarder.py
aws s3 cp webhook_forwarder.zip s3://edx-tools-lambda-webhooks/
rm webhook_forwarder.zip
```
