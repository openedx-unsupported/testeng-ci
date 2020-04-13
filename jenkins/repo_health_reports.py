"""
Script to help create a PR with Repo health report. To be run inside
a Jenkins job that first runs the health checks on a target repo
(see pytest-repo-health and edx-repo-health repos)
"""
from __future__ import absolute_import

import logging

import click
import six
from github import GithubObject

from .github_helpers import (authenticate_with_github, branch_exists,
                             close_existing_pull_requests, connect_to_repo,
                             create_branch, create_pull_request,
                             get_modified_files_list, update_list_of_files)

logging.basicConfig()
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


@click.command()
@click.option(
    '--sha',
    help="Sha of the merge commit to base the new PR off of",
    required=True,
)
@click.option(
    '--repo_root',
    help="Path to local repository to run repo health on. "
    required=True,
)
@click.option(
    '--repo_name',
    help="Name of Repo in Github "
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
def main(sha, repo_root, repo_name, org, user_reviewers, team_reviewers):
    """
    Inspect the results of running ``make upgrade`` and create a PR with the
    changes if appropriate.
    """
    LOGGER.info("Authenticating with Github")
    github_instance = authenticate_with_github()

    # Last folder in repo_root should be the repository
    directory_list = repo_root.split("/")
    repository = connect_to_repo(github_instance, repo_name)

    modified_files_list = get_modified_files_list(repo_root)
    if modified_files_list:
        branch = "refs/heads/jenkins/repo_health-{}".format(sha[:7])
        if branch_exists(repository, branch):
            LOGGER.info("Branch for this sha already exists")
        else:
            LOGGER.info("modified files: {}".format(modified_files_list))
            user = github_instance.get_user()
            commit_sha = update_list_of_files(
                repository,
                repo_root,
                modified_files_list,
                "Repo Health Report",
                sha,
                user.name
            )
            create_branch(repository, branch, commit_sha)

            LOGGER.info("Checking if there's any old pull requests to delete")
            deleted_pulls = close_existing_pull_requests(repository, user.login, user.name)

            pr_body = "Review Repo Health Report."
            for num, deleted_pull_number in enumerate(deleted_pulls):
                if num == 0:
                    pr_body += "\n\nDeleted obsolete pull_requests:"
                pr_body += "\nhttps://github.com/{}/{}/pull/{}".format(org, repository_name, deleted_pull_number)

            LOGGER.info("Creating a new pull request")

            # If there are reviewers to be added, split them into python lists
            if isinstance(user_reviewers, (str, six.text_type)) and user_reviewers:
                user_reviewers = user_reviewers.split(',')
            else:
                user_reviewers = GithubObject.NotSet

            if isinstance(team_reviewers, (str, six.text_type)) and team_reviewers:
                team_reviewers = team_reviewers.split(',')
            else:
                team_reviewers = GithubObject.NotSet

            create_pull_request(
                repository,
                'Repo Health Report',
                pr_body,
                'master',
                branch,
                user_reviewers=user_reviewers,
                team_reviewers=team_reviewers
            )
    else:
        LOGGER.info("No changes needed")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
