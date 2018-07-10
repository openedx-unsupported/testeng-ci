# -*- coding: UTF-8 -*-

# Occasionally, pull requests never get updated with codecov results, which
# can create a lot of difficulty in getting the pr merged. However, this is
# purely anecdotal.

# This script attempts to determine the extent of the issue. It scans a series
# of repositories that are currently reporting coverage metrics to codecov,
# and collects the length of time it took for codecov to post back a status context
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
    'edx/bok-choy',
    'edx/completion',
    'edx/course-discovery',
    'edx/credentials',
    'edx/ecommerce',
    'edx/edx-analytics-dashboard',
    'edx/edx-analytics-pipeline',
    'edx/edx-app-android',
    'edx/edx-app-ios',
    'edx/edx-drf-extensions',
    'edx/edx-enterprise',
    'edx/edx-enterprise-data',
    'edx/edx-gomatic',
    'edx/edx-notes-api',
    'edx/edx-platform',
    'edx/edx-proctoring',
    'edx/edx-video-pipeline',
    'edx/edx-video-worker',
    'edx/studio-frontend',
    'edx/XBlock',
    'edx/xqueue',
]


def is_recent(activity_time, time_frame=3600):
    """
    determine if a timestamp occurred between now (UTC) and time_frame
    """
    activity_age = datetime.datetime.utcnow() - activity_time
    return activity_age.total_seconds() < time_frame


def is_head_recent(pull_request, time_frame=3600):
    """
    determine if the head commmit pull request has been pushed between now and
    time_frame by seeing if any of the status contexts on the head commit were
    posted within said time frame. This seems to be the only way to derive
    this information, as the Github API does not serve information about when
    a commit is pushed.
    """
    try:
        head_commit = get_head_commit(pull_request)
    except IndexError:
        logger.info('{} has no commits. Skipping'.format(pull_request.title))
        return False
    statuses = head_commit.get_combined_status().statuses
    return any(
        [is_recent(dt, time_frame) for dt in [s.updated_at for s in statuses]]
    )


def get_recent_pull_requests(repo, time_frame=3600):
    """
    given a repository, retrieve all pull requests that have received
    updated status contexts within a given time frame
    """
    recent_pull_requests = []
    for pr in repo.get_pulls(state="all", sort="updated", direction="desc"):
        # since the pull requests are sorted by 'updated_at', once we reach
        # pull requests that have not been updated in a week, stop searching
        if not is_recent(pr.updated_at, 604800):
            break
        if is_head_recent(pr, time_frame):
            recent_pull_requests.append(pr)

    logger.info("Found {} recent pull requests".format(
        len(recent_pull_requests)
    ))
    return recent_pull_requests


def get_head_commit(pull_request):
    return pull_request.get_commits().reversed[0]


def has_context_posted(context_name, statuses):
    return context_name in [status.context for status in statuses]


def get_context_update_time(context, statuses):
    return filter(
        lambda x: x.context == context, statuses
    )[0].updated_at.replace(microsecond=0)


def get_context_state(context, statuses):
    return filter(lambda s: s.context == context, statuses)[0].state


def get_context_age(statuses, codecov_context, trigger_context):
    """
    get the age of a given codecov context. This is done by computing
    the difference between when the context that triggers codecov was
    posted and when codecov results were posted, or, in the case that
    they haven't yet, now.
    """
    # get the context that should trigger the codecov context
    trigger_context_update_time = get_context_update_time(
        trigger_context, statuses
    )

    if has_context_posted(codecov_context, statuses):
        codecov_context_update_time = get_context_update_time(
            codecov_context, statuses
        )
        context_age = codecov_context_update_time - trigger_context_update_time
        logger.info("'{}' posted {} seconds after {} was posted".format(
            codecov_context, context_age, trigger_context
        ))
        posted = True
    else:
        current_timestamp = datetime.datetime.utcnow().replace(microsecond=0)
        context_age = current_timestamp - trigger_context_update_time
        logger.info(
            "'{}' has still not posted {} seconds after {} was posted".format(
                codecov_context, context_age, trigger_context
            )
        )
        posted = False
    context_age_in_seconds = int(context_age.total_seconds())
    # occasionally, codecov can be posted back to the pull request before
    # travis. This is the case in which a complex travis file runs different
    # sharded tasks, one of which submits coverage data. This will result
    # in a negative age for the codecov context. Treat these as 0, since
    # their impact is not important.
    if context_age_in_seconds < 0:
        context_age_in_seconds = 0
    return posted, context_age_in_seconds, trigger_context_update_time


def gather_codecov_metrics(all_repos, time_frame):
    """
    scan all pertinent repos for metrics on how long it took for codecov
    to report back following a 'triggering' context posting back to a
    pull request. Return a list of JSON objects storing this data.
    """
    logger.info(
        'Gathering codecov response metrics on pull requests ' +
        'updated within the last {} seconds'.format(time_frame)
    )

    results = []

    for repo in [r for r in all_repos if r.full_name in REPOS]:

        logger.info('Checking {} for recent PRs'.format(repo.full_name))
        prs = get_recent_pull_requests(repo, time_frame=time_frame)
        # skip repos not updated within this 'time_frame'
        if not prs:
            logger.info(
                'No recent pull requests found in {}.'.format(repo.full_name)
            )
            continue

        for pr in prs:
            pr_title = unicode(pr.title)
            logger.info('Analyzing pr {}'.format(pr_title))
            head_commit = get_head_commit(pr)
            head_status = head_commit.get_combined_status().statuses
            # mapping of status contexts that generate code coverage data
            # and send it to codecov to the codecov status contexts for
            # said data
            context_map = {
                'continuous-integration/travis-ci/pr': 'codecov/patch',
                'continuous-integration/travis-ci/push': 'codecov/project',
                'jenkins/python': 'codecov/project'
            }
            for trigger_context, codecov_context in context_map.iteritems():
                # skip prs that have not been posted to by their trigger status
                if not has_context_posted(trigger_context, head_status):
                    logger.info(
                        "Context '{}' has not posted yet. Skipping".format(
                            trigger_context
                        )
                    )
                    continue
                # skip prs in which the trigger context has failed. This means
                # that coverage results have not been sent to codecov
                if get_context_state(trigger_context, head_status) != 'success':
                    logger.info("Context '{}' failed. Skipping".format(
                        trigger_context
                    ))
                    continue
                posted, context_age, trigger_posted_at = get_context_age(
                    head_status, codecov_context, trigger_context
                )
                result = {
                    'repo': repo.full_name,
                    'pull_request': pr_title,
                    'commit': head_commit.sha,
                    'trigger_context_posted_at': str(trigger_posted_at),
                    'codecov_received':  posted,
                    'codecov_received_after': context_age,
                    'context': codecov_context
                }
                results.append(result)
    return results


def main():
    try:
        token = os.environ.get('GITHUB_TOKEN')
    except KeyError:
        logger.error('No value set for GITHUB_TOKEN. Please try again')
        sys.exit(1)

    gh = Github(token)
    # Only consider pull requests created within this time frame (in seconds)
    time_frame = os.environ.get('PULL_REQUEST_TIME_FRAME', 3600)

    all_repos = gh.get_user().get_repos()
    results = gather_codecov_metrics(all_repos, time_frame)

    json_data = {'results': results}
    outfile_name = 'codecov_metrics.json'
    try:
        logger.info('Writing results to {}'.format(outfile_name))
        with open(outfile_name, 'w') as outfile:
            json.dump(json_data, outfile, separators=(',', ':'))
            outfile.write('\n')
    except OSError:
        logger.error('Unable to write data to {}'.format(outfile_name))
        sys.exit(1)

if __name__ == "__main__":
    main()
