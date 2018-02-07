import click
from github import Github
import logging
import os
import sys

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _get_github_token():
    """
    Get the github oauth token from
    the environment variable GITHUB_TOKEN
    """
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        logger.error(
            "No value found for environment variable GITHUB_TOKEN"
        )
        sys.exit(1)
    return token


@click.command()
@click.option(
    '--pr_number',
    help="The PR number of a pull request on edx-platform. "
         "This PR will receive a comment when its tests finish. ",
    required=True,
)
def main(pr_number):
    """
    Checks a pull request on edx-platform to see if tests are finished. If they
    are, it comments on the PR to notify the user. If not, the script exits.
    """
    github_token = _get_github_token()
    github_instance = Github(github_token)

    repos_list = github_instance.get_user().get_repos()

    repository = None
    for repo in repos_list:
        if repo.name == "edx-platform":
            repository = repo

    if not repository:
        logger.error(
            "Could not access edx-platform. Please make sure "
            "the GITHUB_TOKEN is valid."
        )
        sys.exit(1)

    try:
        pr_number_int = int(pr_number)
        pull_request_object = repository.get_pull(pr_number_int)
    except:
        logger.error("Invalid PR number given.")
        sys.exit(1)

    head_commit = pull_request_object.get_commits().reversed[0]
    for status in head_commit.get_combined_status().statuses:
        if status.state == 'pending':
            logger.info(
                "Other tests are still pending on this PR. Exiting"
            )
            sys.exit()

    comment = "Your PR has finished running tests."
    try:
        pull_request_object.create_issue_comment(comment)
    except:
        logger.error(
            "Failed to add issue comment to PR."
        )
        sys.exit(1)
    logger.info("Successfully commented on PR.")


if __name__ == "__main__":
    main()
