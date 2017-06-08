import base64
import json
import logging
import os
import re
from six.moves.urllib.parse import urlparse
from constants import *

import botocore.session
from botocore.vendored.requests import post, get

logging.basicConfig()
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


def _get_num_tries():
    """
    Get the number of tries desired. If Jenkins does not trigger
    all of the expected jobs on the first try, the webhook will be resent
    until this number is hit.
    Return a integer
    """
    num_tries_string = os.environ.get('NUM_TRIES')

    try:
        num_tries_int = int(num_tries_string)
    except:
        raise StandardError(
            'Environment variable NUM_TRIES was not set to a valid integer'
        )

    return num_tries_int


def _get_credentials_from_s3(jenkins_url):
    """
    Get jenkins credentials from s3 bucket.
    The bucket name should be an environment variable, and the
    object name should be specified in a dict (with the
    Jenkins url as the key) in the constants.py file.
    The expected object is a JSON file formatted as:
    {
        "username": "sampleusername",
        "api_token": "sampletoken"
    }
    """
    bucket_name = os.environ.get('S3_CREDENTIALS_BUCKET')

    if not bucket_name:
        raise StandardError(
            'Environment variable S3_CREDENTIALS_BUCKET was not set'
        )

    session = botocore.session.get_session()
    client = session.create_client('s3')

    try:
        file_name = JENKINS_S3_OBJECTS[jenkins_url] + '.json'
    except:
        raise StandardError(
            'Jenkins url not found in JENKINS_S3_OBJECTS'
        )

    creds_file = client.get_object(Bucket=bucket_name, Key=file_name)
    creds = json.loads(creds_file['Body'].read())

    if not creds.get("username") or not creds.get("api_token"):
        raise StandardError(
            'Credentials file needs both a '
            'username and api_token attribute'
        )

    return creds["username"], creds["api_token"]


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


def _parse_hook_for_testing_info(payload, event_type):
    """
    Parse the webhook to find the commit sha,
    as well as the arguments needed to find the
    jobs_list.
    Returns:
        Tuple with commit sha and list of jobs that
        should be triggered. If the event type is not
        pull_request, return empty values
    """
    ignore = False

    if event_type == 'pull_request':
        # find the repo and whether the pr is being merged
        repository = payload['pull_request']['base']['repo']['name']
        is_merge = payload['pull_request']['merged']

        # check if the base branch is an openedx release branch
        base_ref = payload['pull_request']['base']['ref']
        if re.match('^((?!open-release\/).)*$', base_ref):
            # if the base_ref does not include open-release/
            # the master jobs will be kicked off
            target = "master"
        elif base_ref == EUCALYTPUS_BRANCH:
            target = "eucalyptus"
        elif base_ref == FICUS_BRANCH:
            target = "ficus"
        else:
            # no jobs are expected by ghprb in this case
            ignore = True

        if payload['action'] == 'closed':
            sha = payload['pull_request']['merge_commit_sha']
            if not is_merge:
                # if the PR was closed and not merged,
                # no jobs will be triggered
                ignore = True
        else:
            # PR was either "opened" or "synchronized" which is
            # when a new commit is pushed to the PR
            sha = payload['pull_request']['head']['sha']
    else:
        # unsupported event type, return None for both values
        ignore = True

    # if we are ignoring this hook, return None values,
    # otherwise, return sha, jobs_list
    if ignore:
        # we don't care about these so assign None, None
        return (None, None)
    else:
        # find the jobs list for this hook
        jobs_list = _get_jobs_list(repository, target, event_type, is_merge)

    return sha, jobs_list


def _get_jobs_list(repository, target, event_type, is_merge):
    """
    Find the list of jobs that the webhook should kick
    off on Jenkins.
    """
    jobs_list = []
    if repository == 'edx-platform':
        if event_type == 'pull_request':
            if target == 'master':
                if is_merge:
                    jobs_list = EDX_PLATFORM_MASTER
                else:
                    jobs_list = EDX_PLATFORM_PR
            if target == 'eucalyptus':
                if is_merge:
                    jobs_list = EDX_PLATFORM_EUCALYPTUS_MASTER
                else:
                    jobs_list = EDX_PLATFORM_EUCALYPTUS_PR
            if target == 'ficus':
                if is_merge:
                    jobs_list = EDX_PLATFORM_FICUS_MASTER
                else:
                    jobs_list = EDX_PLATFORM_FICUS_PR
    elif repository == 'edx-platform-private':
        if event_type == 'pull_request':
            if is_merge:
                jobs_list = EDX_PLATFORM_PRIVATE_MASTER
            else:
                jobs_list = EDX_PLATFORM_PRIVATE_PR
    elif repository == 'edx-e2e-tests':
        if event_type == 'pull_request':
            if not is_merge:
                jobs_list = EDX_E2E_PR

    return jobs_list


def _all_tests_triggered(jenkins_url, sha, jobs_list):
    """
    Check to see if the sha has triggered each
    job in the jobs_list. Looks at both the queue
    as well as currently running builds
    """
    jenkins_username, jenkins_token = _get_credentials_from_s3(jenkins_url)

    queued = _get_queued_builds(
        jenkins_url, jenkins_username, jenkins_token
    )
    running = _get_running_builds(
        jenkins_url, jenkins_username, jenkins_token
    )
    queued_or_running = queued + running

    return _builds_contain_tests(queued_or_running, sha, jobs_list)


def _builds_contain_tests(builds, sha, jobs_list):
    """
    From the list of all running/queued builds, check
    to see if the webhook's sha has kicked off every
    job in the jobs_list
    """
    triggered_jobs = []
    contain_jobs = True
    if jobs_list:
        for build in builds:
            build_job_name = build['job_name']
            build_sha = build['sha']
            if (build_job_name in jobs_list
                    and build_sha == sha
                    and build_job_name not in triggered_jobs):
                triggered_jobs.append(build_job_name)
        if set(triggered_jobs) != set(jobs_list):
            contain_jobs = False

    return contain_jobs


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
                if (param['name'] == 'sha1' or
                        param['name'] == 'ghprbActualCommit'):
                    sha = param['value']
                    if build_status == 'queued':
                        job_name = executable['task']['name']
                    elif build_status == 'running':
                        url = executable['url']
                        m = re.search(
                            r'/job/([^/]+)/.*',
                            urlparse(url).path
                        )
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
    # set a timeout for the request to avoid timing out of lambda
    url = '%s/queue/api/json?depth=0' % (jenkins_url)
    try:
        response = get(
            url,
            auth=(jenkins_username, jenkins_token),
            timeout=(3.05, 10)
        )
        response_json = response.json()

        # Find all builds in the queue and add them to a list
        [builds.extend(_parse_executables_for_builds(executable, build_status))
         for executable in response_json['items']]
    except:
        logger.warning('Timed out while trying to access the queue.')

    return builds


def _get_running_builds(jenkins_url, jenkins_username, jenkins_token):
    """
    Find all builds that are currently running
    """
    builds = []
    build_status = 'running'

    # Use Jenkins REST API to get info on all workers
    # set a timeout for the request to avoid timing out of lambda
    url = '%s/computer/api/json?depth=2' % (jenkins_url)
    try:
        response = get(
            url,
            auth=(jenkins_username, jenkins_token),
            timeout=(3.05, 10)
        )
        response_json = response.json()

        # Find all builds being executed and add them to a list
        for worker in response_json['computer']:
            for executor in worker['executors'] + worker['oneOffExecutors']:
                executable = executor['currentExecutable']
                if executable:
                    builds.extend(
                        _parse_executables_for_builds(executable, build_status)
                    )
    except:
        logger.warning('Timed out while trying to access the running builds.')

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

        # Get the sha and jobs list (if applicable), as well as
        # the max number of retries for sending the hook.
        event_type = headers.get('X-GitHub-Event')
        sha, jobs_list = _parse_hook_for_testing_info(payload, event_type)
        num_tries = _get_num_tries()

        # Send it off!
        # If the url is a known jenkins instance (in constants.py),
        # check to make sure all jobs have been triggered. If they
        # haven't, continue trying up to "num_tries" times.
        # Save up the final results for later processing rather than
        # letting the errors get raised.
        # That way we can process all records and urls.
        for attempt in range(0, num_tries):
            # rather than retrying one url continuously, and risking
            # timeout, loop through urls for each retry
            url_iterator = 0
            while url_iterator < len(urls):
                # the url will likely have a path, such as /ghprbhook/,
                # find just the base_url
                url_parsed = urlparse(urls[url_iterator])
                base_url = url_parsed.scheme + '://' + url_parsed.netloc

                # send the message!
                result = _send_message(urls[url_iterator], payload, headers)

                # Check if base_url is in JENKINS_S3_OBJECTS
                if base_url in JENKINS_S3_OBJECTS:
                    if jobs_list:
                        logger.info(
                            "Checking if Jenkins jobs have been triggered..."
                        )
                        if _all_tests_triggered(base_url, sha, jobs_list):
                            logger.info(
                                "All Jenkins jobs have been triggered "
                                "for sha: '{}'".format(sha)
                            )
                            results.append(result)
                            # url satisifed, delete from list
                            del urls[url_iterator]
                        else:
                            url_iterator += 1
                            if attempt == num_tries - 1:
                                # jobs were not all triggered for url
                                logger.error(
                                    "Unable to trigger all jobs for "
                                    "sha: '{}'".format(sha)
                                )
                                # no more tries, so save result
                                results.append(result)
                            else:
                                logger.info(
                                    "Not all Jenking Jobs were triggered. "
                                    "This webhook will be resent..."
                                )
                    else:
                        logger.info("No Jenkins Jobs expected for this sha.")
                        # no jobs expected, delete from list
                        del urls[url_iterator]
                else:
                    logger.info("No Jenkins Jobs expected for this url.")
                    # not a jenkins url, delete from list
                    del urls[url_iterator]
            if not len(urls):
                # if there are no more urls that need jenkins jobs
                # triggered, no need for more retries
                break

    results_count = _process_results_for_failures(results)

    if results_count.get('failure'):
        raise StandardError(results_count)

    return results_count
