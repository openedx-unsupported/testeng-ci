"""
Script to help create a PR with python library upgrades. To be run inside
a Jenkins job that first runs `make upgrade`
"""
from __future__ import absolute_import

import click

from jenkins.pull_request_creator import PullRequestCreator


@click.command()
@click.option(
    '--sha',
    help="Sha of the merge commit to base the new PR off of",
    required=True,
)
@click.option(
    '--repo_root',
    help="Path to local repository to run make upgrade on. "
         "Make sure the path includes the repo name",
    required=True,
)
@click.option(
    '--org',
    help="The github organization for the repository to run make upgrade on.",
    required=True,
)
@click.option(
    '--user_reviewers',
    help="Comma seperated list of Github users to be tagged on pull requests",
    default=None
)
@click.option(
    '--team_reviewers',
    help="Comma seperated list of Github teams to be tagged on pull requests",
    default=None
)
def main(sha, repo_root, org, user_reviewers, team_reviewers):
    """
    Inspect the results of running ``make upgrade`` and create a PR with the
    changes if appropriate.
    """

    pr_body = "Python requirements update.  Please review the [changelogs](" \
              "https://openedx.atlassian.net/wiki/spaces/TE/pages/1001521320/Python+Package+Changelogs" \
              ") for the upgraded packages."

    pull_request_creator = PullRequestCreator(sha=sha, repo_root=repo_root, branch_name="upgrade-python-requirements",
                                              user_reviewers=user_reviewers, team_reviewers=team_reviewers,
                                              commit_message="Updating Python Requirements",
                                              pr_title="Python Requirements Update", pr_body=pr_body, org=org)

    pull_request_creator.create(delete_old_pull_requests=True)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
