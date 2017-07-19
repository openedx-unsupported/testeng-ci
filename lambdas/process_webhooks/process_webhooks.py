import base64
import json
import logging
import os
import re
from six.moves.urllib.parse import urlparse
from constants import *

import boto3
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

    # Based on the X-Github-Event header, determine the
    # proper endpoint for the target url.
    # PR's and Issue Comments use the ghprb Jenkins plugin
    # Pushes use the Github Jenkins plugin
    if event_type in ["issue_comment", "pull_request"]:
        endpoint = "ghprbhook/"
    elif event_type == "push":
        endpoint = "github-webhook/"
    elif event_type == "ping":
        return None
    else:
        raise StandardError(
            "The Spigot does not support webhooks of "
            "type: {}".format(event_type)
        )

    return url + "/" + endpoint


def _get_credentials_from_s3(jenkins_url):
    """
    Get jenkins credentials from s3 bucket.
    The expected object is a JSON file formatted as:
    {
        "username": "sampleusername",
        "api_token": "sampletoken"
    }
    """
    # For both build and test jenkins, we can use
    # the same credentials
    session = botocore.session.get_session()
    client = session.create_client('s3')

    try:
        file_name = JENKINS_S3_OBJECTS[jenkins_url] + '.json'
    except:
        raise StandardError(
            'Jenkins url not found in JENKINS_S3_OBJECTS'
        )

    creds_file = client.get_object(
        Bucket=CREDENTIALS_BUCKET,
        Key=CREDENTIALS_FILE
    )
    creds = json.loads(creds_file['Body'].read())

    if not creds.get("username") or not creds.get("api_token"):
        raise StandardError(
            'Credentials file needs both a '
            'username and api_token attribute'
        )

    return creds["username"], creds["api_token"]


def _get_jobs_list(repository, target, event_type):
    """
    Find the list of jobs that the webhook should kick
    off on Jenkins.
    """
    jobs_list = []

    # Based on the repo, target, and event type find the
    # desired list of tests from constants.py
    if repository == 'edx-platform':
        if target == 'master':
            if event_type == 'push':
                jobs_list = JOBS_DICT['EDX_PLATFORM_MASTER']
            elif event_type == 'pull_request':
                jobs_list = JOBS_DICT['EDX_PLATFORM_PR']
        elif target == 'ficus':
            if event_type == 'push':
                jobs_list = JOBS_DICT['EDX_PLATFORM_FICUS_MASTER']
            elif event_type == 'pull_request':
                jobs_list = JOBS_DICT['EDX_PLATFORM_FICUS_PR']
        elif target == 'ginkgo':
            if event_type == 'push':
                jobs_list = JOBS_DICT['EDX_PLATFORM_GINKGO_MASTER']
            elif event_type == 'pull_request':
                jobs_list = JOBS_DICT['EDX_PLATFORM_GINKGO_PR']
    elif repository == 'edx-platform-private':
        if event_type == 'push':
            jobs_list = JOBS_DICT['EDX_PLATFORM_PRIVATE_MASTER']
        elif event_type == 'pull_request':
            jobs_list = JOBS_DICT['EDX_PLATFORM_PRIVATE_PR']

    return jobs_list


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
        if payload['action'] != 'closed':
            # PR was either "opened" or "synchronized" which is
            # when a new commit is pushed to the PR
            repository = payload['pull_request']['base']['repo']['name']
            ref = payload['pull_request']['base']['ref']
            sha = payload['pull_request']['head']['sha']
        else:
            ignore = True
    elif event_type == 'push':
        try:
            repository = payload['repository']['name']
            ref = payload['ref']
            sha = payload['head_commit']['id']
        except:
            # If the hook is missing any of these ignore it.
            # One example where this happens is the
            # push hook triggered to a feature branch
            # when it is being merged.
            ignore = True
    else:
        # Unsupported event type, return None for both values
        ignore = True

    # Find the target based on the base_ref
    if not ignore:
        if ref == "refs/heads/master":
            target = "master"
        elif ref in RELEASE_BRANCHES:
            # find the target from constants.py
            target = RELEASE_BRANCHES[ref]
        else:
            # no jobs are expected in this case
            ignore = True

    # If we are ignoring this hook, return None values,
    # otherwise, return sha, jobs_list
    if ignore:
        # We don't care about these so assign None, None
        return (None, None, None)
    else:
        # Find the jobs list for this hook
        jobs_list = _get_jobs_list(repository, target, event_type)

    return sha, jobs_list, target


def _parse_executable_for_builds(
    executable, build_status, event_type, target, hook_sha
):
    """
    Parse executable to find the sha and job name of
    queued/running builds.
    Return list of jobs with the sha that triggered
    them
    """
    builds = []
    if event_type == "pull_request":
        # All PR jobs show the sha that triggered them inside its
        # parameters.
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
                        if sha == hook_sha:
                            builds.append({
                                'job_name': job_name,
                                'sha': sha
                            })
    elif event_type == "push":
        if build_status == 'running':
            # Based on the branch that is being merged into
            # (master or one of the RELEASE_BRANCHES) find the sha
            # and job being executed.
            target_branch = None
            if target == "master":
                target_branch = "origin/master"
            else:
                for release in RELEASE_BRANCHES:
                    if RELEASE_BRANCHES[release] == target:
                        target_branch = release

            if target_branch:
                for action in executable['actions']:
                    if 'buildsByBranchName' in action:
                        if action['buildsByBranchName'][target_branch]:
                            sha = (
                                action['buildsByBranchName'][target_branch]
                                ['revision']['SHA1']
                            )
                            url = executable['url']
                            m = re.search(
                                r'/job/([^/]+)/.*',
                                urlparse(url).path
                            )
                            job_name = m.group(1)
                            if sha == hook_sha:
                                builds.append({
                                    'job_name': job_name,
                                    'sha': sha
                                })
        elif build_status == 'queued':
            # For queued master builds, the only way to find out
            # if a sha has executed a build is to find queued subsets,
            # look at the sha1 parameter, and the upstream
            # project associated with it.
            job_name = sha = None
            for action in executable['actions']:
                if 'parameters' in action:
                    for param in action['parameters']:
                        if (param['name'] == 'sha1'):
                            sha = param['value']
                if 'causes' in action:
                    for cause in action['causes']:
                        job_name = cause['upstreamProject']
            # If both values exist for this executable,
            # save the pair as a build.
            if job_name and sha == hook_sha:
                builds.append({
                    'job_name': job_name,
                    'sha': sha
                })

    return builds


def _get_queued_builds(
    jenkins_url, jenkins_username, jenkins_token, event_type, target, sha
):
    """
    Find all builds currently in the queue
    """
    build_status = 'queued'
    builds = []

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
        for executable in response_json['items']:
            builds.extend(
                _parse_executable_for_builds(
                    executable, build_status, event_type, target, sha
                )
            )
    except:
        logger.warning('Timed out while trying to access the queue.')

    return builds


def _get_running_builds(
    jenkins_url, jenkins_username, jenkins_token, event_type, target, sha
):
    """
    Find all builds that are currently running
    """
    build_status = 'running'
    builds = []

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
                        _parse_executable_for_builds(
                            executable, build_status, event_type, target, sha
                        )
                    )
    except:
        logger.warning('Timed out while trying to access the running builds.')

    return builds


def _get_all_triggered_builds(jenkins_url, event_type, target, sha):
    """
    Check to see if the sha has triggered each
    job in the jobs_list. Looks at both the queue
    as well as currently running builds
    """
    jenkins_username, jenkins_token = _get_credentials_from_s3(jenkins_url)

    queued = _get_queued_builds(
        jenkins_url, jenkins_username, jenkins_token, event_type, target, sha
    )
    running = _get_running_builds(
        jenkins_url, jenkins_username, jenkins_token, event_type, target, sha
    )
    queued_or_running = queued + running

    return queued_or_running


def _get_triggered_jobs_from_list(builds, already_triggered, sha, jobs_list):
    """
    From the list of all running/queued builds, find which
    jobs from the jobs_list have been triggered.
    """
    triggered_jobs = already_triggered if already_triggered else []
    if builds and jobs_list:
        for build in builds:
            build_job_name = build['job_name']
            build_sha = build['sha']
            if (build_job_name in jobs_list
                    and build_sha == sha
                    and build_job_name not in triggered_jobs):
                triggered_jobs.append(build_job_name)

    return triggered_jobs


def _all_jobs_triggered(triggered_jobs, jobs_list):
    """
    Check to see if all jobs in the jobs list
    have been triggered.
    """
    return set(triggered_jobs) == set(jobs_list)


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

        if not url:
            # If url is None, swallow the hook, since it is just a ping
            return (
                "Received a ping webhook. No action required."
            )

        event_type = headers.get('X-GitHub-Event')

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

        # Get the commit sha and list of expected jobs to be executed
        # from this webhook.
        sha, jobs_list, target = _parse_hook_for_testing_info(
            payload, event_type
        )

        # If there is no jobs_list then no Jenkins jobs are expected
        if not jobs_list:
            logger.info(
                "No platform jobs are expected to be triggered "
                "by this hook."
            )
            return (
                "Webhook successfully sent to url: {}".format(url)
            )

        # Get all triggered running/ queued builds from Jenkins
        # that match the desired sha.
        triggered_builds = _get_all_triggered_builds(
            url, event_type, target, sha
        )

        # Check if this hook has already successfully triggered some jobs.
        # If so, its possible that the jobs have finished executing since
        # the hooks first transmission.
        if event.get('already_triggered'):
            already_triggered_builds = event.get('already_triggered')
            logger.info(
                'The following jobs have been previously '
                'triggered: {}'.format(already_triggered_builds)
            )
        else:
            already_triggered_builds = None

        triggered_jobs_from_list = _get_triggered_jobs_from_list(
            triggered_builds, already_triggered_builds, sha, jobs_list
        )

        if _all_jobs_triggered(triggered_jobs_from_list, jobs_list):
            logger.info(
                "All Jenkins jobs have been triggered "
                "for sha: '{}'".format(sha)
            )
        else:
            # Not all tests were triggered, queue this hook
            # for later processing.
            if from_queue and already_triggered != triggered_jobs_from_list:
                # The message came from the queue, and not all the expected
                # jobs have been triggered. However, more jobs were kicked
                # off, so we need to update that by adding a new hook to the
                # queue, and deleting the old. Send a unique error message
                # so send_from_queue knows to delete it despite the failure.
                event.update({'already_triggered': triggered_jobs_from_list})
                queue_name = _get_target_queue()
                _response = _send_to_queue(event, queue_name)
                raise StandardError(
                    "More jobs triggered, but unable to trigger all jobs."
                )
            elif not from_queue:
                event.update({'already_triggered': triggered_jobs_from_list})
                queue_name = _get_target_queue()
                _response = _send_to_queue(event, queue_name)
            raise StandardError(
                "Unable to trigger all jobs for "
                "sha: '{}'".format(sha)
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
