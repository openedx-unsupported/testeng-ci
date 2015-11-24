# pylint: disable=redefined-outer-name, invalid-name

"""
Creates a new release candidate branch and makes a pull request
for it into the 'release' branch.
"""

from __future__ import print_function

import argparse

from release.github_api import GithubApi
from release.utils import default_expected_release_date


class NoValidCommitsError(Exception):
    """
    Error indicating that there are now commits that do not have status
    problems.
    """
    pass


def _build_parser():
    """ Creates an option parser for this command """
    expected_date = default_expected_release_date()
    result = argparse.ArgumentParser(description="""
        Create a new release candidate branch and associated pull request.
        """)
    result.add_argument('--release-date', nargs=1, help="""
        Specify a date that the release branch is expected to be deployed.
        Should be in YYYY-MM-DD format. If not passed, defaults to the
        next upcoming Tuesday, which is currently %s.
        """ % expected_date.date().isoformat(), default=expected_date)
    result.add_argument('--org', nargs=1, help="""
        Specify a github organization to work under. Default is 'edx'.
        """, default='aleffert')
    result.add_argument('--repo', nargs=1, help="""
        Specify a github repository to work with. Default is 'edx-platform'.
        """, default='edx-platform')
    return result


def most_recent_good_commit(github_api):
    """
    Returns the most recent commit on master that has passed the tests
    """
    def _is_commit_successful(commit_sha):
        """
        Returns whether the passed commit has passed all its tests.
        Ensures there is at least one status update so that
        commits whose tests haven't started yet are not valid.
        """
        statuses = github_api.commit_statuses(commit_sha)

        joiner = lambda cur, status: status['state'] == "success" and cur
        passed_tests = reduce(joiner, statuses, True)
        return len(statuses) > 0 and passed_tests

    commits = github_api.commits()

    result = None
    for commit in commits:
        if _is_commit_successful(commit['sha']):
            result = commit
            return result['sha']

    # no result
    print("Couldn't find a recent commit without test failures. Aborting")
    raise NoValidCommitsError()

parser = _build_parser()
args = parser.parse_args()

github_api = GithubApi(args.org, args.repo)

print("Fetching commits...")
commit_hash = most_recent_good_commit(github_api)
branch_name = "rc/%s" % args.release_date.date().isoformat()

print("Branching {rc} off {sha}".format(rc=branch_name, sha=commit_hash))
github_api.create_branch(branch_name, commit_hash)

print("Creating Pull Request for {rc} into master".format(rc=branch_name))
request_title = "Release Candidate {rc}".format(rc=branch_name)
github_api.create_pull_request(branch_name, title=request_title)
