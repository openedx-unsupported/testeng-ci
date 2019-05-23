import logging
import os
import sys

import click
import six
from github import Github

from github_helpers import connect_to_repo, get_github_token

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
    ACTIONS = ('ignore', 'delete_old_comments', 'notify_tests_completed',)

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
        return self._action_str('ignore') in six.text_type(pr.body)

    def delete_old_comments(self, pr):
        comments = pr.get_issue_comments()
        for comment in comments:
            if comment.user.login == self.name:
                logger.info(
                    "Old comment found on PR. Deleting"
                )
                comment.delete()

    def delete_old_comments_marker(self, pr):
        return True

    def notify_tests_completed(self, pr):
        """Post a notification on the PR that tests have finished running."""
        comment = self.generate_notification_message(pr)
        try:
            pr.create_issue_comment(comment)
        except:
            logger.error("Failed to add issue comment to PR.")
            sys.exit(1)
        else:
            logger.info("Successfully commented on PR.")

    def get_head_commit(self, pr):
        """
        Return the HEAD commit from a given pull request. Occasionally, a pull
        request can have no commits (for instance, if it has been reset). In
        this case, exit the script, as there is nothing else to do.
        """
        commits = pr.get_commits()
        if not list(commits):
            logger.error("This pull request has no commits. Exiting.")
            sys.exit()
        head_commit = commits.reversed[0]
        return head_commit

    def notify_tests_completed_marker(self, pr):
        head_commit = self.get_head_commit(pr)
        for status in head_commit.get_combined_status().statuses:
            if status.state == 'pending':
                logger.info(
                    "Other tests are still pending on this PR. Exiting"
                )
                break
        else:
            return True

    def generate_notification_message(self, pr):
        failing_contexts = self.get_failures(pr)
        if not failing_contexts:
            status_description = "There were no failures."
        else:
            status_description = "The following contexts failed:\n{}".format(
                '\n'.join(["* {}".format(f) for f in failing_contexts])
            )
        comment = "Your PR has finished running tests. {}".format(
            status_description
        )
        return comment

    def get_failures(self, pr):
        """ return a list of the contexts that recently failed on a given pr """
        head_commit = self.get_head_commit(pr)
        failures = filter(
            lambda status: status.state in ["failure", "error"],
            head_commit.get_combined_status().statuses
        )
        return map(lambda status: status.context, failures)

    def _action_str(self, action):
        return '{}: {}'.format(self.name, action)


@click.command()
@click.option(
    '--repo',
    help="Repository of pull request. Defaults to edx-platform",
    default="edx-platform"
)
@click.option(
    '--pr_number',
    help="The PR number of a pull request. "
         "This PR will receive a comment when its tests finish.",
    required=True,
)
def main(repo, pr_number):
    """
    Checks a pull request in Github to see if tests are finished. If they
    are, it comments on the PR to notify the user. If not, the script exits.
    """
    bot = EdxStatusBot(token=get_github_token())
    repo = connect_to_repo(bot.github, repo)

    try:
        pr = repo.get_pull(int(pr_number))
    except:
        logger.error("Invalid PR number given.")
        sys.exit(1)
    else:
        bot.act_on(pr)


if __name__ == "__main__":
    main()
