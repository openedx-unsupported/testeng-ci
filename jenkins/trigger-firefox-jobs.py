from github import Github
import logging
import os
import sys

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

PR_NUMBER = 17734

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


def main():
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
        pull_request_object = repository.get_pull(PR_NUMBER)
    except:
        logger.error("Invalid PR number given.")
        sys.exit(1)

    comment = "jenkins run firefox upgrade bokchoy"
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
