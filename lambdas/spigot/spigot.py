import base64
import json
import logging
import os

import boto3
from botocore.vendored.requests import post

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


def _get_target_urls():
    """
    Get the target URLs for the processed hooks from a comma delimited
    list of URLs, set in an OS environment variable.

    Return a list of target URLs
    """
    url = os.environ.get('TARGET_URLS')
    if not url:
        raise StandardError('Environment variable TARGET_URLS was not set')

    return url.split(',')


def _get_target_queue():
    """
    Get the target SQS name for the processed hooks from the
    OS environment variable.

    Return the name of the queue
    """
    queue_name = os.environ.get('TARGET_QUEUE')
    if not queue_name:
        raise StandardError('Environment variable TARGET_QUEUE was not set')

    return queue_name


def _get_state_from_s3():
    """
    Get spigot_state from config file from s3.
    The bucket is the same as where the spigot code lives.
    The object should be "spigot_config.json"
    The expected object is a JSON file formatted as:
    {
        "spigot_state": "ON" | "OFF"
    }
    """
    client = boto3.client('s3')

    try:
        file = client.get_object(
            Bucket='edx-tools-spigot',
            Key='spigot_config.json'
        )
    except:
        raise StandardError(
            'Unable to get spigot_config.json file from S3'
        )

    body = json.loads(file['Body'].read())

    if not body.get("spigot_state"):
        raise StandardError(
            'Config file missing key: "spigot_state"'
        )

    return body["spigot_state"]


def _add_gh_header(data_object, headers):
    """
    Get the X-GitHub-Event header from the original request
    data, add this to the headers, and return the results.

    Raise an error if the GitHub event header is not found.
    """
    gh_headers = data_object.get('headers')
    gh_event = gh_headers.get('X-GitHub-Event')
    if not gh_event:
        msg = 'X-GitHub-Event header was not found in {}'.format(gh_headers)
        raise ValueError(msg)

    logger.debug('GitHub event was: {}'.format(gh_event))
    headers['X-GitHub-Event'] = gh_event
    return headers


def _send_message(url, payload, headers):
    """ Send the webhook to the endpoint via an HTTP POST.
    Args:
        url (str): Target URL for the POST request
        payload (dict): Payload to send
        headers (dict): Dictionary of headers to send
    Returns:
        dict with k,v pairs for the original data, response,
        and exception, as applicable.
    """
    result = {
        'url': url,
        'payload': payload,
        'headers': headers
    }
    try:
        response = post(url, json=payload, headers=headers, timeout=(3.05, 10))
        #  trigger the exception block for 4XX and 5XX responses
        response.raise_for_status()
        result['response'] = response

    # Catch the errors because you may have another URL or record to process
    except Exception as exc:
        result['exception'] = exc

    return result


def _send_to_queue(event, queue_name):
    """
    Send the webhook to the SQS queue.
    """
    try:
        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName=queue_name)
    except:
        raise StandardError('Unable to find the target queue')

    try:
        response = queue.send_message(MessageBody=json.dumps(event))
    except:
        raise StandardError('The message could not be sent to queue')

    return response


def _get_from_queue(queue_name):
    """
    Get a webhook from the SQS queue.
    """
    try:
        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName=queue_name)
    except:
        raise StandardError('Unable to find the target queue')

    try:
        # get a list of 1 message size from the queue
        message_list = queue.receive_messages(
            MaxNumberOfMessages=1,
            WaitTimeSeconds=3
        )

        # return just the message rather than the list
        return message_list[0]
    except:
        raise StandardError('Unable to get a message from the queue')


def _delete_from_queue(queue_name, message):
    """
    Delete a webhook from the SQS queue.
    """
    try:
        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName=queue_name)
    except:
        raise StandardError('Unable to find the target queue')

    try:
        msg_receipt = message.receipt_handle
        entry = {'Id': 'id', 'ReceiptHandle': msg_receipt}
    except:
        raise StandardError(
            'Unable to get necessary message attributes '
            'for deletion. ReceiptHandle are required')

    try:
        response = queue.delete_messages(Entries=[entry])
    except:
        raise StandardError('Unable to delete message from queue')


def _process_results_for_failures(results):
    """ Process the results of the HTTP requests and log any errors.
    Args:
        results (list): List of results from the attempted HTTP POSTs
    Returns:
        Dict with the count of successes and failures
    """
    results_count = {'success': 0, 'failure': 0}

    for result in results:
        base_msg = "URL: {url}, HEADERS: {headers}, PAYLOAD: {payload}".format(
            url=result.get('url'),
            headers=result.get('headers'),
            payload=result.get('payload')
        )
        exc = result.get('exception')
        if exc:
            results_count['failure'] = results_count.get('failure') + 1
            msg = "Could not forward webhook. {} EXCEPTION: {}".format(
                base_msg, exc)
            logger.error(msg)
        else:
            results_count['success'] = results_count.get('success') + 1
            logger.debug("Successfully processed webhook. {}".format(base_msg))

    return results_count


def lambda_handler(event, _context):
    # The header we send should include the original GitHub header,
    # and also is set to send the data in the format that Jenkins expects.
    header = {'Content-Type': 'application/json'}

    if not event:
        # The SQS queue is draining
        logger.info('Draining the queue.')

        # Get a webhook from the queue
        queue_name = _get_target_queue()
        message = _get_from_queue(queue_name)
        data_object = json.loads(message.body)

        # Add the headers from the message response
        headers = _add_gh_header(data_object, header)
        logger.debug("headers are: '{}'".format(headers))
    else:
        # Get the state of the spigot from s3
        spigot_state = _get_state_from_s3()
        logger.info(
            'The spigot state is set to: {}'.format(spigot_state)
        )

        # Add the headers from the event
        headers = _add_gh_header(event, header)
        logger.debug("headers are: '{}'".format(headers))

        if spigot_state == 'ON':
            # No need to manipulate the event, since it
            # is already a json object
            data_object = event
        elif spigot_state == 'OFF':
            # Since the spigot is off, send the event
            # to SQS for future processing.
            queue_name = _get_target_queue()
            response = _send_to_queue(event, queue_name)
            return response

    # Get the url(s) that the webhook will be sent to
    urls = _get_target_urls()
    results = []

    # We had stored the payload to send in the
    # 'body' node of the data object.
    payload = data_object.get('body')
    logger.debug("payload is: '{}'".format(payload))

    # Send it off!
    # Save up the results for later processing rather than letting
    # the errors get raised.
    # That way we can process all records and urls.
    for url in urls:
        results.append(_send_message(url, payload, headers))

    results_count = _process_results_for_failures(results)

    if results_count.get('failure'):
        if event:
            # Since the queue is not draining,
            # and there was a failure, store the webhook
            # in the SQS queue to avoid losing data.
            logger.info('Storing the failed hook in SQS')
            queue_name = _get_target_queue()
            response = _send_to_queue(data_object, queue_name)
        raise StandardError(results_count)

    if not event:
        # Since the queue is draining, and there were
        # no failures, delete the webhook from the
        # SQS queue.
        logger.info('Deleting the hook from SQS')
        _delete_from_queue(queue_name, message)

    return results_count
