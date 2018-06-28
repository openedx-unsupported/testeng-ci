# -*- coding: UTF-8 -*-

# Occasionally, pull requests never get updated with codecov results, which
# can create a lot of difficulty in getting the pr merged. However, this is
# purely anecdotal.

# This script attempts to determine the extent of the issue. It scans a series
# of repositories that are currently reporting coverage metrics to codecov,
# and collects the lenght of time it took for codecov to post back a status context
# (if at all).

# This script should be run periodically in order to get a good understanding
# of the state of codecov response times.

import os
import sys
import datetime
import logging
import json

from github import Github

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)
REPOS = [
    'edx/edx-app-ios',
    'edx/edx-enterprise',
    'edx/ecommerce',
    'edx/studio-frontend',
    'edx/xqueue'
    'edx/edx-gomatic',
    'edx/edx-drf-extensions',
    'edx/edx-analytics-dashboard',
    'edx/edx-proctoring',
    'edx/credentials',
    'edx/course-discovery',
    'edx/edx-video-pipeline',
    'edx/edx-analytics-pipeline'
    'edx/completion',
    'edx/XBlock',
    'edx/edx-enterprise-data',
    'edx/edx-notes-api',
    'edx/edx-app-android',
    'edx/edx-video-worker',
    'edx/edx-platform'
]


def is_recent(pull_request, time_frame=3600):
    """
    determine if a pull request has been committed to between now (UTC)
    and a given time frame
    """
    newest_commit = pull_request.get_commits().reversed[0]
    commit_pushed_at = get_commit_time(newest_commit)
    activity_age = datetime.datetime.utcnow() - commit_pushed_at
    return activity_age.total_seconds() < time_frame


def get_recent_pull_requests(repo, time_frame=3600):
    """
    given a repository, retrieve pull requests that have had activity within
    a time frame
    """
    # debug
    logger.info(repo.full_name)
    num = repo.get_pulls()
    recent_pull_requests = [
        pr for pr in repo.get_pulls() if is_recent(pr, time_frame)
    ]
    logger.info("Found {} recent pull requests".format(len(recent_pull_requests)))
    return recent_pull_requests


def get_commit_time(commit):
    """
    return the time that a given commit was pushed
    """
    return datetime.datetime.strptime(
        commit.last_modified, "%a, %d %b %Y %H:%M:%S %Z"
    )


def get_context_age(commit, context_name):
    """
    Given a commit and a context (i.e. 'codecov/patch'), determine:
    a) if the context has been posted onto the commit
    b) the age of the context update. In other words, the time diff between
    the commit being pushed and the context being posted
    """
    commit_received_at = get_commit_time(commit)
    statuses = commit.get_combined_status().statuses
    if context_name in [c.context for c in statuses]:
        context = filter(lambda x: x.context == context_name, statuses)[0]
        context_age = context.updated_at - commit_received_at
        context_age_in_seconds = context_age.total_seconds()
        log_msg = "'{}' posted within {}s of the commit being pushed".format(
            context_name, context_age_in_seconds
        )
        return True, context_age_in_seconds
    else:
        current_age = datetime.datetime.utcnow() - commit_received_at
        current_age_in_seconds = current_age.total_seconds()
        logger.info("'{}' has not posted {}s after commit was pushed".format(
            context_name, current_age_in_seconds))
        return False, current_age_in_seconds


def main():
    try:
        token = os.environ.get('GITHUB_TOKEN')
    except KeyError:
        logger.error('No value set for GITHUB_TOKEN. Please try again')
        sys.extit(1)

    gh = Github(token)
    # Only consider pull requests created within this time frame (in seconds)
    pull_request_time_frame = os.environ.get('PULL_REQUEST_TIME_FRAME', 3600)

    logger.info(
        'Gathering codecov response metrics on pull requests ' +
        'updated within the last {} seconds'.format(pull_request_time_frame)
    )

    results = []

    all_repos = gh.get_user().get_repos()
    for repo in [r for r in all_repos if r.full_name in REPOS]:

        logging.info('Searching for recent pull requests in {}'.format(repo.full_name))
        # skip repos not updated within this 'time_frame'
        prs = get_recent_pull_requests(repo, time_frame=pull_request_time_frame)
        if not prs:
            logger.info(
                'Repo {} does not contain any recent pull requests.'.format(repo.full_name)
            )
            continue

        for pr in prs:
            newest_commit = pr.get_commits().reversed[0]
            pr_title = unicode(pr.title)
            logger.info(u"Analyzing commit {} on pull request '{}'".format(
                newest_commit.sha, pr_title))
            for context in ['codecov/project', 'codecov/patch']:
                # edx-platform does not run codecov/patch, so skip it
                if repo.full_name == 'edx/edx-platform' and context == 'codecov/patch':
                    continue
                posted, context_age = get_context_age(newest_commit, context)
                result = {
                    'repo': repo.full_name,
                    'pull_request': pr_title,
                    'commit': newest_commit.sha,
                    'commit_pushed_at': str(get_commit_time(newest_commit)),
                    'codecov_received':  posted,
                    'codecov_received_at': context_age,
                    'context': context
                }
                results.append(result)

    json_data = {'results': results}
    outfile_name = 'codecov_metrics.json'
    try:
        logger.info('Writing results to {}'.format(outfile_name))
        with open(outfile_name, 'w') as outfile:
            json.dump(json_data, outfile, separators=(',', ':'))
            outfile.write('\n')
    except OSError:
        logger.error('Unable to write data to {}'.foramt(outfile_name))
        sys.exit(1)

if __name__ == "__main__":
    main()
