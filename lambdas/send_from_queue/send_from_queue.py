from __future__ import absolute_import

import json
import logging
import os
import sys

import boto3
from requests import post

logger = logging.getLogger()

# First log the function load message, then change
# the level to be configured via environment variable.
logger.setLevel(logging.INFO)
logger.info('Loading function')

# Log level is set as a string, default to 'INFO'
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
numeric_level = getattr(logging, log_level, None)
if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: {}'.format(log_level))
logger.setLevel(numeric_level)


def _get_target_queue():
    """
    Get the target SQS name for the processed hooks from the
    OS environment variable.

    Return the name of the queue
    """
    queue_name = os.environ.get('TARGET_QUEUE')
    if not queue_name:
        raise Exception(
            "Environment variable TARGET_QUEUE was not set"
        )

    return queue_name


def _get_queue_object(queue_name):
    """
    Connect with SQS via boto and return an object representing
    the queue.
    """
    try:
        sqs_resource = boto3.resource('sqs')
        queue_object = sqs_resource.get_queue_by_name(QueueName=queue_name)
    except:
        raise Exception(
            "Unable to connect to the SQS queue"
        )

    return queue_object


def _get_api_url():
    """
    Find the url of the API Gateway by getting its id from boto

    Return the url
    """
    try:
        api_client = boto3.client('apigateway')
        api_list = api_client.get_rest_apis()
    except:
        logger.error(
            "Unable to connect to the apigateway"
        )

    for api in api_list.get("items"):
        if api.get("name") == "edx-tools-webhooks-processing":
            api_id = api.get("id")
            break

    if api_id:
        # Create the url based on the api id
        api_url = (
            "https://{}.execute-api.us-east-1.amazonaws.com"
            "/prod/webhooks"
        ).format(api_id)

        return api_url
    else:
        logger.error(
            "Could not find an api id for the "
            "edx-tools-webhooks-processing API"
        )
        sys.exit(1)


def _is_queue_empty(queue_name):
    """
    Determine whether or not the sqs queue is empty.
    """
    try:
        sqs_client = boto3.client('sqs')
        queue_url_response = sqs_client.get_queue_url(
            QueueName=queue_name
        )
        queue_url = queue_url_response['QueueUrl']
    except:
        raise Exception(
            "Unable to get the queue url"
        )

    try:
        response = sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['ApproximateNumberOfMessages']
        )
        # Convert to an integer
        num_messages = int(
            response['Attributes']['ApproximateNumberOfMessages']
        )
    except:
        raise Exception(
            "Unable to get ApproximateNumberOfMessages from queue"
        )

    if num_messages == 0:
        return True
    else:
        return False


def _get_from_queue(queue_object):
    """
    Get webhooks from the SQS queue for processing.
    """
    try:
        # Get up to 10 messages from the SQS queue.
        # 10 is the maximum allowed by this boto method.
        # If there are fewer than 10 messages on the queue,
        # it will return however many exist.
        message_list = queue_object.receive_messages(
            MaxNumberOfMessages=10,
            WaitTimeSeconds=3
        )

        return message_list
    except:
        raise Exception(
            "Unable to get messages from the queue"
        )


def _delete_from_queue(queue_object, message):
    """
    Delete a webhook from the SQS queue.
    """
    try:
        msg_receipt = message.receipt_handle
        msg_id = message.message_id
        entry = {'Id': msg_id, 'ReceiptHandle': msg_receipt}
    except:
        raise Exception(
            'Unable to get necessary message attributes '
            'for deletion. message_id and '
            'ReceiptHandle are required'
        )

    try:
        response = queue_object.delete_messages(Entries=[entry])
    except:
        raise Exception(
            'Unable to delete message {} from queue'.format(msg_id)
        )


def lambda_handler(event, _context):
    # Get the queue name from the env variable and get
    # a queue object representing it from boto.
    queue_name = _get_target_queue()
    queue_object = _get_queue_object(queue_name)

    if _is_queue_empty(queue_name):
        empty_msg = "No visible messages in the queue to clear"
        logger.debug(empty_msg)
        return empty_msg

    # Rather than hardcoding the api url, get it from boto.
    # Add the query param so the process_webhooks lambda
    # knows the webhook is coming from the queue.
    api_url_query = _get_api_url() + "?from_queue=True"

    # The SQS queue is draining
    logger.info('Attempting to drain the queue.')

    # Process hooks from the SQS queue until it is empty. If the queue is
    # large, this may mean processing items until the lambda times out.
    while not _is_queue_empty(queue_name):
        # Get messages from the sqs queue
        logger.info('Fetching messages from the queue.')
        messages = _get_from_queue(queue_object)

        for message in messages:
            message_body = json.loads(message.body)

            payload = message_body.get("body")
            headers = message_body.get("headers")

            if not payload or not headers:
                # The hook is missing either the body or
                # the headers. Throw an error
                raise Exception(
                    "Unable to parse the body and headers "
                    "from the following webhook in the "
                    "queue. {}".format(message_body)
                )

            # Send the SQS message to the API Gateway
            response = post(
                api_url_query,
                json=payload,
                headers=headers,
                timeout=(3.05, 30)
            )

            # If there was a problem, raise an error
            response.raise_for_status()

            # Otherwise, delete the message since it has been processed
            _delete_from_queue(queue_object, message)

    # If this gets reached before a timeout, the queue had been emptied
    return "The queue has been cleared."
