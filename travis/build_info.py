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


def get_active_jobs(build_id):
    """
    Get the jobs for a build
    return: list of dicts
    """
    jobs = []
    req = requests.get(
        BASE_URL + 'v3/build/{build_id}/jobs'.format(build_id=build_id)
    )
    job_resp = req.json()
    for job in job_resp['jobs']:
        if job['state'] not in ["passed", "failed"]:
            jobs.append(job)
    return jobs


def active_job_counts(jobs):
    """
    Returns counts of total jobs, and
    total running jobs for a given list

    This method assumes it has a received
    a list of active jobs.

    Possible job states:
     * received
     * queued
     * created
     * passed, failed
     * started

    """
    job_count = len(jobs)
    started_jobs_count = 0
    for job in jobs:
        if job['state'] == 'started':
            started_jobs_count += 1

    return job_count, started_jobs_count


def repo_active_build_count(builds):
    """
    Returns counts of total builds, and total
    running builds for a given list of them

    This method assumes it has received a list
    of active builds.

    Possible build states:
    * created
    * started
    * finished

    """
    build_count = 0
    started_count = 0
    for build in builds:
        build_count += 1
        if build.get('state') == 'started':
            started_count += 1

    return build_count, started_count


def get_job_counts(org):
    """
    Total job counts (active and total) for
    an org
    """
    total_job_count = 0
    total_started_job_count = 0

    repos = get_repos(org)
    for repo in repos:
        repo_builds = get_active_builds(org, repo)
        repo_jobs = 0
        repo_started_jobs = 0
        for build in repo_builds:
            build_jobs = get_active_jobs(build['id'])
            total, started = active_job_counts(build_jobs)
            total_job_count += total
            total_started_job_count += started
            repo_jobs += total
            repo_started_jobs += started
        logger.debug("----> " + repo)
        debug_msg = "total jobs: {total}, started jobs: {started}".format(
            total=repo_jobs,
            started=repo_started_jobs
        )
        logger.debug(debug_msg)
    logger.debug('--------')
    logger.info('overall_jobs_total=' + str(total_job_count))
    logger.info('overall_jobs_started=' + str(total_started_job_count))


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
    if args.task_class.upper() == 'JOB':
        get_job_counts(org=args.org)
    else:
        get_build_counts(org=args.org)

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s')
    main(sys.argv[1:])
