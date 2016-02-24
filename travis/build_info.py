"""
Gather Travis usage info in real-time using Travis REST APIs

This only applies to travis instances that do not require
authorization (e.g., travis-ci.org). Auth is a #TODO

"""

import argparse
import logging
import requests
import sys


logger = logging.getLogger(__name__)

BASE_URL = 'https://api.travis-ci.org/'


def get_repos(org):
    """
    Returns list of active repos in a given org.
    """
    repo_list = []
    # Note: One call is needed if org has <= 100 active repos.
    # If org has > 100, this code will need to be modified
    #  to include 'offset' requests
    req = requests.get(
        BASE_URL + 'v3/owner/{org}/repos?active=true'.format(org=org)
    )
    if req.status_code != 200:
        raise requests.HTTPError(req.status_code)
    repos = req.json()
    try:
        for repo in repos.get('repositories'):
            repo_list.append(repo['name'])
    except KeyError:
        raise KeyError("Cannot parse response")

    return repo_list


def get_active_builds(org, repo):
    """
    Returns list of active builds for a given repo slug
    """
    repo_slug = '{org}/{repo}'.format(org=org, repo=repo)
    req = requests.get(
        BASE_URL + 'repos/{repo_slug}/builds'.format(repo_slug=repo_slug)
    )
    build_list = req.json()
    active_build_list = []
    for build in build_list:
        if build.get('state') != 'finished':
            active_build_list.append(build)
    return active_build_list


# @property
# def build_id(build_item):
#
#     return build_item['id']
#

def get_jobs(build_id):
    """
    Get the jobs for a build
    return: list of dicts
    """
    req = requests.get(
        BASE_URL + 'v3/build/{build_id}/jobs'.format(build_id=build_id)
    )
    return req['jobs']


# @property
# def job_state(job):
#     """
#     possible states:
#     * received
#     * queued
#     * created
#     * is there a started?
#     """
#
#     return job['state']


def repo_active_build_count(builds):
    """
    Returns counts of total builds, and total
    running builds for a given list of them

    This method assumes it has received a list
    of active builds.
    """
    build_count = 0
    started_count = 0
    for build in builds:
        build_count += 1
        if build.get('state') == 'started':
            started_count += 1

    return build_count, started_count


def repo_active_job_count(active_builds):
    """
    Returns count of active jobs associated with builds in a
    given repo.
    """
    job_count = 0
    started_job_count = 0
    for build in active_builds:
        if build['stage'] != 'finished':
            jobs = get_jobs(build['id'])
            for job in jobs:
                if job['state'] != 'finished':
                    job_count += 1
                    if job['state'] != 'queued':
                        started_job_count += 1

    return job_count, started_job_count


def main(raw_args):
    """
    Parse args and execute the script according to those args
    """
    desc = (
        "Obtain information on active/waiting Travis builds."
    )
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        '--org', '-o',
        dest='org',
        help='Travis org',
        required=True
        )
    parser.add_argument(
        '--task-class',  # this is not doing anything for now.
        dest='task_class',
        help="Select build or job. A build is composed of one or many jobs.",
        choices=[
            'BUILD', 'build',
            'JOB', 'job',
        ],
        default="BUILD",
    )
    parser.add_argument(
        '--log-level',
        dest='log_level',
        help="set logging level",
        choices=[
            'DEBUG', 'debug',
            'INFO', 'info',
            'WARNING', 'warning',
            'ERROR', 'error',
            'CRITICAL', 'critical',
        ],
        default="INFO",
    )
    args = parser.parse_args(raw_args)

    # Set logging level
    logging.getLogger(__name__).setLevel(args.log_level.upper())
    get_build_counts(org=args.org)


def get_build_counts(org):
    """
    Find out all the active and waiting builds for a given
    Github/Travis org
    """
    repos = get_repos(org)
    org_build_count = 0
    org_build_started_count = 0

    for repo in repos:
        repo_builds = get_active_builds(org, repo)
        logger.debug("--->" + repo)

        repo_build_total, num_started = repo_active_build_count(repo_builds)

        debug_string = "total: {builds}, started: {builds_started}".format(
            builds=repo_build_total,
            builds_started=num_started,
        )
        logger.debug(debug_string)

        org_build_count += repo_build_total
        org_build_started_count += num_started

    logger.debug('--------')
    logger.info("overall_total=" + str(org_build_count))
    logger.info("overall_started=" + str(org_build_started_count))
    logger.info(
        "overall_queued=" + str(org_build_count - org_build_started_count)
    )


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s')
    main(sys.argv[1:])
