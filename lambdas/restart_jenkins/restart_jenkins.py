from __future__ import absolute_import

import json
import logging
import os

import botocore.session
from botocore.vendored.requests import get, post

CREDENTIALS_BUCKET = "edx-tools-credentials"
CREDENTIALS_FILE = "jenkins_safe_restart_credentials.json"

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


def _get_base_url():
    """Get the base URL from the OS environment variable. """
    url = os.environ.get('BASE_URL')
    if not url:
        raise Exception(
            "Environment variable BASE_URL was not set"
        )
    # Let the URL be specified with or without a / at the end
    return url.rstrip('/')


def _get_credentials_from_s3():
    """
    Get jenkins credentials from s3 bucket.
    The expected object is a JSON file formatted as:
    {
        "username": "sampleusername",
        "api_token": "sampletoken"
    }
    """
    session = botocore.session.get_session()
    client = session.create_client('s3')

    creds_file = client.get_object(
        Bucket=CREDENTIALS_BUCKET,
        Key=CREDENTIALS_FILE
    )
    creds = json.loads(creds_file['Body'].read())

    if not creds.get('username') or not creds.get('api_token'):
        raise Exception(
            'Credentials file needs both a '
            'username and api_token attribute'
        )
    return (creds['username'], creds['api_token'])


def lambda_handler(_event, _context):
    jenkins_url = _get_base_url()
    auth = _get_credentials_from_s3()
    headers = None

    # If CSRF is enabled, you need to get a crumb
    # to send in the header of your POST request.
    response = get(
        '{}/crumbIssuer/api/json'.format(jenkins_url),
        auth=auth,
        timeout=(3.05, 30)
    )

    # You will get a 404 if CSRF is not enabled,
    # in which case you don't need to do anything.
    # So only take action if you get a 200.
    if response.status_code == 200:
        crumb = response.json()
        crumb_value = crumb.get('crumb')
        crumb_field = crumb.get('crumbRequestField')
        headers = {crumb_field: crumb_value}

    response = post(
        '{}/safeRestart'.format(jenkins_url),
        auth=auth,
        headers=headers,
        timeout=(3.05, 30)
    )

    # Safe Restart will put the user back at the root.
    # If no jobs are running it will restart
    # immediately and respond with a 503.
    # So we need to raise an error for other 4XX and 5XX
    # responses, but not that one.
    if response.status_code != 503:
        response.raise_for_status()


if __name__ == "__main__":
    lambda_handler(None, None)
