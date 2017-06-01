import base64
import json
import logging
import os
import urllib
import re
from six.moves.urllib.parse import urlparse
from constants import (
    EDX_PLATFORM_MASTER,
    EDX_PLATFORM_PR,
    EDX_PLATFORM_EUCALYPTUS_MASTER,
    EDX_PLATFORM_EUCALYPTUS_PR,
    EDX_PLATFORM_FICUS_MASTER,
    EDX_PLATFORM_FICUS_PR,
    EDX_PLATFORM_PRIVATE_MASTER,
    EDX_PLATFORM_PRIVATE_PR,
    EDX_E2E_PR,
)

import botocore.session
from botocore.vendored.requests import post, get

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


def _get_num_retries():
    """
    Get the number of retries desired. If Jenkins does not trigger
    all of the expected jobs, the webhook will be resent up to
    this number of times.

    Return a integer
    """
    num_retries = os.environ.get('NUM_RETRIES')
    if not isinstance(num_retries, int):
        raise StandardError('Environment variable NUM_RETRIES was not set to a valid integer')
    
    return num_retries


def _get_credentials_from_s3():
    """
    Get jenkins credentials from s3 bucket.
    The bucket name should be an environment variable.
    """
    session = botocore.session.get_session()
    client = session.create_client('s3')

    bucket_name = os.environ.get('S3_CREDENTIALS_BUCKET')

    if not bucket_name:
        raise StandardError('Environment variable S3_CREDENTIALS_BUCKET was not set')

    creds_file = client.get_object(Bucket=bucket_name, Key='credentials.json')
    creds_json = json.loads(creds_file['Body'].read())

    return creds_json["username"], creds_json["api_token"]


def _verify_data(data_string):
    """
    Verify that the data received is in the correct format
    Raise an error if not.
    Return the data as a python object.
    """
    try:
        data_object = json.loads(data_string)

    except ValueError as _exc:
        msg = 'Cannot decode {} into a JSON object'.format(data_string)
        raise ValueError(msg)

    except Exception as exc:
        raise exc

    return data_object


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


def _parse_hook_for_testing_info(data_string):
    """
    Parse the webhook to find the commit sha,
    as well as the arguments needed to find the
    jobs_list.

    Returns:
        Tuple with commit sha and list of jobs that
        should be triggered
    """
    repository = 'edx-e2e-tests'
    target = 'master'
    event_type = 'pull_request'
    sha = "bd6106be30c9f72fb0353028cbd189c476a7c7c6"
    is_merge = False
    # data_object = json.loads(data_string)
    # is_merge = False

    # event_type = headers.get('X-GitHub-Event')
    # if event_type == 'pull_request':
    #     repository = data_object['pull_request']['head']['repo']['name']
    #     target = data_object['pull_request']['head']['ref']
    #     if data_object['action'] == 'opened':
    #         sha = data_object['pull_request']['head']['sha']
    #     elif data_object['action'] == 'closed':
    #         sha = data_object['merge_commit_sha']
    #         if sha != 'null':
    #             is_merge = True
    #             return sha, []

    return sha, _get_jobs_list(repository, target, event_type, is_merge)


def _get_jobs_list(repository, target, event_type, is_merge):
    """
    Find the list of jobs that the webhook should kick
    off on Jenkins.
    """
    if repository == 'edx-platform':
        if event_type == 'pull_request':
            if target == 'master':
                if is_merge:
                    return EDX_PLATFORM_MASTER
                else:
                    return EDX_PLATFORM_PR
            if target == 'eucalyptus':
                if is_merge:
                    return EDX_PLATFORM_EUCALYPTUS_MASTER
                else:
                    return EDX_PLATFORM_EUCALTYPUS_PR
            if target == 'ficus':
                if is_merge:
                    return EDX_PLATFORM_FICUS_MASTER
                else:
                    return EDX_PLATFORM_FICUS_PR
    elif repository == 'edx-platform-private':
        if event_type == 'pull_request':
            if is_merge:
                return EDX_PLATFORM_PRIVATE_MASTER
            else:
                return EDX_PLATFORM_PRIVATE_PR
    elif repository == 'edx-e2e-tests':
        if event_type == 'pull_request':
            if not is_merge:
                return EDX_E2E_PR
    return []


def _all_tests_triggered(jenkins_url, jobs_list, sha):
    """
    Check to see if the sha has triggered each
    job in the jobs_list. Looks at both the queue
    as well as currently running builds
    """
    jenkins_username, jenkins_token = _get_jenkins_credentials()

    queued_or_running = _get_queued_builds(jenkins_url, jenkins_username, jenkins_token) +
                        _get_running_builds(jenkins_url, jenkins_username, jenkins_token)
    return _builds_contain_tests(queued_or_running, sha, jobs_list)


def _builds_contain_tests(builds, sha, jobs_list):
    """
    From the list of all running/queued builds, check
    to see if the webhook's sha has kicked off every
    job in the jobs_list
    """
    if jobs_list:
        for build in builds:
            if build['job_name'] in jobs_list and build['sha'] == sha:
                index = jobs_list.index(build['job_name'])
                del jobs_list[index]
                if len(jobs_list) == 0:
                    return True
        return False
    else:
        return True


def _parse_executables_for_builds(executable, build_status):
    """
    Parse executable to find the sha and job name of
    queued/running builds.
    Return list of jobs with the sha that triggered
    them
    """
    builds = []
    for action in executable['actions']:
        if 'parameters' in action:
            for param in action['parameters']:
                if param['name'] == 'sha1' or param['name'] == 'ghprbActualCommit':
                    sha = param['value']
                    if build_status == 'queued':
                        job_name = executable['task']['name']
                    elif build_status == 'running':
                        url = executable['url']
                        m = re.search(r'/job/([^/]+)/.*', urlparse(url).path)
                        job_name = m.group(1)
                    builds.append({
                        'job_name': job_name,
                        'sha': sha
                    })
    return builds


def _get_queued_builds(jenkins_url, jenkins_username, jenkins_token):
    """
    Find all builds currently in the queue
    """
    builds = []
    build_status = 'queued'

    # Use Jenkins REST API to get info on the queue
    url = '%s/queue/api/json?depth=0' % (jenkins_url)
    response = get(url, auth=(jenkins_username, jenkins_token)).json()

    # Find all builds in the queue and add them to a list
    [builds.extend(_parse_executables_for_builds(executable, build_status)) for executable in response['items']]
    return builds


def _get_running_builds(jenkins_url, jenkins_username, jenkins_token):
    """
    Find all builds that are currently running
    """
    builds = []
    build_status = 'running'

    # Use Jenkins API to get info on all workers
    url = '%s/computer/api/json?depth=2' % (jenkins_url)
    response = get(url, auth=(jenkins_username, jenkins_token)).json()

    # Find all builds being executed and add them to a list
    for worker in response['computer']:
        for executor in worker['executors'] + worker['oneOffExecutors']:
            executable = executor['currentExecutable']
            if executable:
                builds.extend(_parse_executables_for_builds(executable, build_status))
    return builds


def lambda_handler(event, _context):

    urls = _get_target_urls()
    results = []

    # Kinesis stream event format looks like this. data is base64 encoded:
    # {
    # "Records": [{
    #     "SequenceNumber": "n",
    #     "ApproximateArrivalTimestamp": N,
    #     "data": "<ABC>==",
    #     "PartitionKey": "1"}],
    # "NextShardIterator": "abc",
    # "MillisBehindLatest": 0
    # }
    for record in event['Records']:
        k_data = record['kinesis']['data']
        data = base64.b64decode(k_data)
        logger.debug("Decoded payload: '{}'".format(data))

        # Verify that the data received and decoded is in the expected format.
        data_object = _verify_data(data)

        # The header we send should include the original GitHub header,
        # and also is set to send the data in the format that Jenkins expects.
        header = {'Content-Type': 'application/json'}
        headers = _add_gh_header(data_object, header)
        logger.debug("headers are: '{}'".format(headers))

        # Remove the header that we had stored in the data object.
        data_object.pop('headers', None)

        # We had stored the payload to send in the
        # 'body' node of the data object.
        payload = data_object.get('body')
        logger.debug("payload is: '{}'".format(payload))

        # Send it off!
        # Save up the results for later processing rather than letting
        # the errors get raised.
        # That way we can process all records and urls.
        num_retries = _get_num_retries()
        for url in urls:
            url_parsed = urlparse(url)
            # Check if url is a Jenkins instance
            if url_parsed.path contains 'ghprbhook':
                jenkins_url = url_parsed.scheme + '://' + url_parsed.netloc
                for attempt in range(0, num_retries):
                    # get base url
                    jenkins_url = urlparse(url).
                    # send message and check if jobs are triggered
                    result = _send_message(url, payload, headers)
                    sha, jobs_list = _parse_hook_for_testing_info(data_string)

                    if _all_tests_triggered(jobs_list, sha):
                        logger.info("All Jenkins jobs have been triggered for sha: '{}'".format(sha))
                        results.append(result)
                    else:
                        logger.info("The following Jenkins jobs were not triggered: '{}'".format(jobs_list))
                        if attempt == num_retries - 1:
                            # additional action for failures here
                            results.append(result)
                        else:
                            logger.info("Resending webhook...")
            else:
                results.append(_send_message(url, payload, headers))

    results_count = _process_results_for_failures(results)

    if results_count.get('failure'):
        raise StandardError(results_count)

    return results_count