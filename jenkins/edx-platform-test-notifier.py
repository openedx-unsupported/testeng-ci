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
        logger.error("No value found for environment variable GITHUB_TOKEN")
        sys.exit(1)
    return token


class EdxStatusBot:
    """
    A status bot that can perform multiple actions on PRs.

    Looks for lines of the form '{botname}: {action}' in a PR's body to
    determine what actions to take.
    """

    DEFAULT_BOT_NAME = 'edx-status-bot'

    # An ordered list of actions that this bot can take.
    #
    # Each action should correspond to a method name, and each
    # action should have a corresponding `action`_marker method,
    # e.g. 'ignore_marker', which tells whether the action should
    # be taken.
    ACTIONS = ('ignore', 'notify_tests_completed',)

    def __init__(self, token, name=DEFAULT_BOT_NAME):
        self.name = name
        self.token = token
        self.github = Github(self.token)

    def act_on(self, pr):
        for action in self.ACTIONS:
            take_action = getattr(self, action + '_marker')
            if take_action(pr):
                getattr(self, action)(pr)

    def ignore(self, pr):
        """Ignore taking any further actions on this PR."""
        logger.info(
            "PR #{} author doesn't want status updates.".format(pr.number)
        )
        sys.exit()

    def ignore_marker(self, pr):
        return self._action_str('ignore') in pr.body

    def notify_tests_completed(self, pr):
        """Post a notification on the PR that tests have finished running."""
        comment = "Your PR has finished running tests."
        try:
            pr.create_issue_comment(comment)
        except:
            logger.error("Failed to add issue comment to PR.")
            sys.exit(1)
        else:
            logger.info("Successfully commented on PR.")

    def notify_tests_completed_marker(self, pr):
        head_commit = pr.get_commits().reversed[0]
        for status in head_commit.get_combined_status().statuses:
            if status.state == 'pending':
                logger.info(
                    "Other tests are still pending on this PR. Exiting"
                )
                break
        else:
            return True

    def get_repo(self, target_repo):
        repos = self.github.get_user().get_repos()
        for repo in repos:
            if repo.name == target_repo:
                return repo
        else:
            logger.error(
                "Could not access {}. Please make sure the "
                "GITHUB_TOKEN is valid.".format(target_repo)
            )
            sys.exit(1)

    def _action_str(self, action):
        return '{}: {}'.format(self.name, action)


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
    bot = EdxStatusBot(token=_get_github_token())
    repo = bot.get_repo('edx-platform')

    try:
        pr = repo.get_pull(int(pr_number))
    except:
        logger.error("Invalid PR number given.")
        sys.exit(1)
    else:
        bot.act_on(pr)


if __name__ == "__main__":
    main()
