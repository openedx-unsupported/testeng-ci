"""
Class helps create GitHub Pull requests
"""
# pylint: disable=missing-class-docstring,missing-function-docstring,attribute-defined-outside-init
import logging

import click
from github import GithubObject

from .github_helpers import GitHubHelper

logging.basicConfig()
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


class PullRequestCreator:

    def __init__(self, repo_root, branch_name, user_reviewers, team_reviewers, commit_message, pr_title,
                 pr_body):
        self.branch_name = branch_name
        self.pr_body = pr_body
        self.pr_title = pr_title
        self.commit_message = commit_message
        self.team_reviewers = team_reviewers
        self.user_reviewers = user_reviewers
        self.repo_root = repo_root

    github_helper = GitHubHelper()

    def _get_github_instance(self):
        return self.github_helper.get_github_instance()

    def _get_user(self):
        return self.github_instance.get_user()

    def _set_repository(self):
        self.repository = self.github_helper.repo_from_remote(self.repo_root, ['origin'])

    def _set_modified_files_list(self):
        self.modified_files_list = self.github_helper.get_modified_files_list(self.repo_root)

    def _create_branch(self, commit_sha):
        self.github_helper.create_branch(self.repository, self.branch, commit_sha)

    def _set_github_data(self):
        LOGGER.info("Authenticating with Github")
        self.github_instance = self._get_github_instance()
        self.user = self._get_user()

        LOGGER.info("Trying to connect to repo")
        self._set_repository()
        LOGGER.info("Connected to {}".format(self.repository))
        self._set_modified_files_list()
        self.base_sha = self.github_helper.get_current_commit(self.repo_root)

    def _branch_exists(self):
        self.branch = "refs/heads/jenkins/{}-{}".format(self.branch_name, self.base_sha[:7])
        return self.github_helper.branch_exists(self.repository, self.branch)

    def _create_new_branch(self):
        LOGGER.info("modified files: {}".format(self.modified_files_list))
        commit_sha = self.github_helper.update_list_of_files(
            self.repository,
            self.repo_root,
            self.modified_files_list,
            self.commit_message,
            self.base_sha,
            self.user.name
        )
        self._create_branch(commit_sha)

    def _create_new_pull_request(self):
        # If there are reviewers to be added, split them into python lists
        if isinstance(self.user_reviewers, str) and self.user_reviewers:
            user_reviewers = self.user_reviewers.split(',')
        else:
            user_reviewers = GithubObject.NotSet

        if isinstance(self.team_reviewers, str) and self.team_reviewers:
            team_reviewers = self.team_reviewers.split(',')
        else:
            team_reviewers = GithubObject.NotSet

        self.github_helper.create_pull_request(
            self.repository,
            self.pr_title,
            self.pr_body,
            'master',
            self.branch,
            user_reviewers=user_reviewers,
            team_reviewers=team_reviewers
        )

    def delete_old_pull_requests(self):
        LOGGER.info("Checking if there's any old pull requests to delete")
        deleted_pulls = self.github_helper.close_existing_pull_requests(self.repository, self.user.login,
                                                                        self.user.name)

        for num, deleted_pull_number in enumerate(deleted_pulls):
            if num == 0:
                self.pr_body += "\n\nDeleted obsolete pull_requests:"
            self.pr_body += "\nhttps://github.com/{}/pull/{}".format(self.repository.full_name,
                                                                     deleted_pull_number)

    def create(self, delete_old_pull_requests):
        self._set_github_data()

        if not self.modified_files_list:
            LOGGER.info("No changes needed")
            return

        if self._branch_exists():
            LOGGER.info("Branch for this sha already exists")
            return

        self._create_new_branch()

        if delete_old_pull_requests:
            self.delete_old_pull_requests()

        self._create_new_pull_request()


@click.command()
@click.option(
    '--repo-root',
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    required=True,
    help="Directory containing local copy of repository"
)
@click.option(
    '--base-branch-name',
    required=True,
    help="Base name for branch to create. Full branch name will be like jenkins/BASENAME-1234567."
)
@click.option('--commit-message', required=True)
@click.option('--pr-title', required=True)
@click.option('--pr-body', required=True)
@click.option(
    '--user-reviewers',
    default='',
    help="Comma separated list of Github users to be tagged on pull requests"
)
@click.option(
    '--team-reviewers',
    default='',
    help=("Comma separated list of Github teams to be tagged on pull requests. "
          "NOTE: Teams must have explicit write access to the repo, or "
          "Github will refuse to tag them.")
)
@click.option(
    '--delete-old-pull-requests/--no-delete-old-pull-requests',
    default=True,
    help="If set, delete old branches with the same base branch name and close their PRs"
)
def main(
    repo_root, base_branch_name,
    commit_message, pr_title, pr_body,
    user_reviewers, team_reviewers,
    delete_old_pull_requests
):
    """
    Create a pull request with these changes in the repo.

    Required environment variables:

    - GITHUB_TOKEN
    - GITHUB_USER_EMAIL
    """
    creator = PullRequestCreator(
        repo_root=repo_root,
        branch_name=base_branch_name, commit_message=commit_message,
        pr_title=pr_title, pr_body=pr_body,
        user_reviewers=user_reviewers,
        team_reviewers=team_reviewers
    )
    creator.create(delete_old_pull_requests)


if __name__ == '__main__':
    main(auto_envvar_prefix="PR_CREATOR")  # pylint: disable=no-value-for-parameter, unexpected-keyword-arg
