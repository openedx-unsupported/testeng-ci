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


def _get_target_url(headers):
    """
    Get the target URL for the processed hooks from the
    OS environment variable. Based on the GitHub event,
    add the proper endpoint.

    Return the target URL with the appropriate endpoint
    """
    url = os.environ.get('TARGET_URL')
    if not url:
        raise StandardError(
            "Environment variable TARGET_URL was not set"
        )

    event_type = headers.get('X-GitHub-Event')

    if event_type in ["issue_comment", "pull_request"]:
        endpoint = "ghprbhook/"
    elif event_type == "push":
        endpoint = "github-webhook/"
    else:
        raise StandardError(
            "This webhook has an unsupported GitHub event type."
        )

    return url + "/" + endpoint


def _get_target_queue():
    """
    Get the target SQS name for the processed hooks from the
    OS environment variable.

    Return the name of the queue
    """
    queue_name = os.environ.get('TARGET_QUEUE')
    if not queue_name:
        raise StandardError(
            "Environment variable TARGET_QUEUE was not set"
        )

    return queue_name


def _add_gh_header(event, headers):
    """
    Get the X-GitHub-Event header from the original request
    data, add this to the headers, and return the results.

    Raise an error if the GitHub event header is not found.
    """
    gh_headers = event.get('headers')
    gh_event = gh_headers.get('X-GitHub-Event')
    if not gh_event:
        msg = 'X-GitHub-Event header was not found in {}'.format(gh_headers)
        raise ValueError(msg)

    logger.debug('GitHub event was: {}'.format(gh_event))
    headers['X-GitHub-Event'] = gh_event
    return headers


def _is_from_queue(event):
    """
    Check to see if this webhook is being sent from the SQS queue.
    This is important to avoid duplicating the hook in the queue
    in the event of a failure.
    """
    return event.get('from_queue') == "True"


def _send_message(url, payload, headers):
    """ Send the webhook to the endpoint via an HTTP POST.
    Args:
        url (str): Target URL for the POST request
        payload (dict): Payload to send
        headers (dict): Dictionary of headers to send
    Returns:
        The response from the HTTP POST
    """
    response = post(url, json=payload, headers=headers, timeout=(3.05, 30))
    # Trigger the exception block for 4XX and 5XX responses
    response.raise_for_status()
    return response


def _send_to_queue(event, queue_name):
    """
    Send the webhook to the SQS queue.
    """
    try:
        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName=queue_name)
    except:
        raise StandardError("Unable to find the target queue")

    try:
        response = queue.send_message(MessageBody=json.dumps(event))
    except:
        raise StandardError("The message could not be sent to queue")

    return response


def lambda_handler(event, _context):
    # Determine if this message is coming from the queue
    from_queue = _is_from_queue(event)

    # The header we send should include the original GitHub header,
    # and also is set to send the data in the format that Jenkins expects.
    header = {'Content-Type': 'application/json'}

    # Add the headers from the event
    headers = _add_gh_header(event, header)
    logger.debug("headers are: '{}'".format(headers))

    # Get the state of the spigot from the api variable
    spigot_state = event.get('spigot_state')
    logger.info(
        "spigot_state is set to: {}".format(spigot_state)
    )

    if spigot_state == "ON":
        # Get the url that the webhook will be sent to
        url = _get_target_url(headers)

        # We had stored the payload to send in the
        # 'body' node of the data object.
        payload = event.get('body')
        logger.debug("payload is: '{}'".format(payload))

        # Send it off!
        try:
            _result = _send_message(url, payload, headers)
        except:
            if not from_queue:
                # The transmission was a failure, if it's not
                # already in the queue, add it.
                queue_name = _get_target_queue()
                _response = _send_to_queue(event, queue_name)
            raise StandardError(
                "There was an error sending the message "
                "to the url: {}".format(url)
            )

        return (
            "Webhook successfully sent to url: {}".format(url)
        )
    elif spigot_state == "OFF":
        # Since the spigot is off, send the event
        # to SQS for future processing. However,
        # if the message is already in the queue do
        # nothing.
        if from_queue:
            raise StandardError(
                "The spigot is OFF. No messages should be "
                "sent from the queue."
            )
        else:
            queue_name = _get_target_queue()
            _response = _send_to_queue(event, queue_name)

            return (
                "Webhook successfully sent to queue: {}".format(queue_name)
            )
    else:
        raise StandardError(
            "API Gateway stage variable spigot_state "
            "was not correctly set. Should be ON or OFF, "
            "was: {}".format(spigot_state)
        )
