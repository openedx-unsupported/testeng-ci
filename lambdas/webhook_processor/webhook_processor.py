import base64
import json
import os
import urllib

from botocore.vendored.requests import post

import logging
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
    Get the target URLs for the processed hooks from a comma delimited list of URLs,
    set in an OS environment variable.

    Return a list of target URLs
    """
    url = os.environ.get('TARGET_URLS')
    if not url:
        raise StandardError('Environment variable TARGET_URLS was not set')

    return url.split(',')


def _verify_data(data_string):
    """
    Verify that the data received is in the correct format
    Raise an error if not.
    Return the data as a python object.
    """
    try:
        data_object = json.loads(data_string)

    except ValueError as _exc:
        raise ValueError('Cannot decode {} into a JSON object'.format(data_string))

    except Exception as exc:
        raise exc

    return data_object


def _add_gh_header(data_object, headers):
    """
    Get the X-GitHub-Event header from the original request
    data, add this to the headers, and return the results

    Raise an error if the GitHub event header is not found.
    """
    gh_headers = data_object.get('headers')
    gh_event = gh_headers.get('X-GitHub-Event')
    if not gh_event:
        raise ValueError('X-GitHub-Event header was not found in {}'.format(gh_headers))

    logger.debug('GitHub event was: {}'.format(gh_event))
    headers['X-GitHub-Event'] = gh_event
    return headers


def _send_message(url, payload, headers):
    """ Send the webhook to the endpoint via an HTTP POST.
    Args:
        url (str): Target URL for the POST request
        payload (str): Payload string to send
        headers (dict): Dictionary of headers to send
    Returns:
        dict with k,v pairs for original data and the response and exception, as applicable
    """
    result = {
        'url': url,
        'payload': payload,
        'headers': headers
    }
    try:
        response = post(url, data=payload, headers=headers, timeout=(3.05, 10))
        response.raise_for_status()   # trigger the exception block for 4XX and 5XX responses
        result['response'] = response

    # Catch the errors because you may have another URL or record to process
    except Exception as exc:
        result['exception'] = exc

    return result


def _process_results_for_failures(results):
    """ Process the results of the HTTP requests to the URL endpoints and log any errors
    Args:
        results (list): List of results from the attempted HTTP POSTs  
    Returns:
        Dict with the count of successes and failures
    """
    results_count = {'success': 0, 'failure': 0}
    
    for result in results:
        base_msg = "URL: {url}, HEADERS: {headers}, PAYLOAD: {payload}".format(
            url = result.get('url'),
            headers = result.get('headers'),
            payload = result.get('payload')
        )
        exc = result.get('exception')
        if exc:
            results_count['failure'] = results_count.get('failure') + 1
            logger.error("Could not forward webhook. {} EXCEPTION: {}".format(base_msg, exc))
        else:
            results_count['success'] = results_count.get('success') + 1
            logger.debug("Successfully processed webhook. {}".format(base_msg))

    return results_count


def lambda_handler(event, _context):

    urls = _get_target_urls()
    results = []

    # Kinesis stream event format looks like this, where Data is base64 encoded:
    # {
    # "Records": [{"SequenceNumber": "n", "ApproximateArrivalTimestamp": N, "Data": "<ABC>==", "PartitionKey": "1"}],
    # "NextShardIterator": "abc",
    # "MillisBehindLatest": 0
    # }
    for record in event['Records']:
        k_data = record['Data']
        data = base64.b64decode(k_data)
        logger.debug("Decoded payload: '{}'".format(data))

        # Verify that the data received and decoded is in the expected format.
        data_object = _verify_data(data)

        # The header we send should include the original GitHub header,
        # and also is set to send the data in the format that Jenkins expects.
        headers = _add_gh_header(data_object, {'Content-Type': 'application/x-www-form-urlencoded'})

        # Create the payload string for Jenkins
        payload = 'payload={}'.format(urllib.quote_plus(data))
        logger.debug("payload is: '{}'".format(payload))

        # Send it off!
        # Save up the results for later processing rather than letting the errors get raised.
        # That way we can process all records and urls.
        for url in urls:
            results.append(_send_message(url, payload, headers))

    results_count = _process_results_for_failures(results)

    if results_count.get('failure'):
        raise StandardError(results_count)

    return results_count
