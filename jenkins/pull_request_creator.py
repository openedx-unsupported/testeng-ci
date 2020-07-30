"""
Class helps create GitHub Pull requests
"""

from __future__ import absolute_import

import logging
import six
from github import GithubObject

from .github_helpers import GitHubHelper

logging.basicConfig()
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


class PullRequestCreator:

    def __init__(self, sha, repo_root, branch_name, user_reviewers, team_reviewers, commit_message, pr_title,
                 pr_body, org=''):
        self.branch_name = branch_name
        self.pr_body = pr_body
        self.pr_title = pr_title
        self.commit_message = commit_message
        self.team_reviewers = team_reviewers
        self.user_reviewers = user_reviewers
        self.org = org
        self.repo_root = repo_root
        self.sha = sha

    github_helper = GitHubHelper()

    def _get_github_instance(self):
        return self.github_helper.get_github_instance()

    def _get_user(self):
        return self.github_instance.get_user()

    def _set_repository(self):
        self.repository = self.github_helper.connect_to_repo(self.github_instance, self.repository_name)

    def _set_modified_files_list(self):
        self.modified_files_list = self.github_helper.get_modified_files_list(self.repo_root)

    def _create_branch(self, commit_sha):
        self.github_helper.create_branch(self.repository, self.branch, commit_sha)

    def _set_github_data(self):
        LOGGER.info("Authenticating with Github")
        self.github_instance = self._get_github_instance()
        self.user = self._get_user()

        # Last folder in repo_root should be the repository
        directory_list = self.repo_root.split("/")
        self.repository_name = directory_list[-1]
        LOGGER.info(u"Trying to connect to repo: {}".format(self.repository_name))
        self._set_repository()
        self._set_modified_files_list()

    def _branch_exists(self):
        self.branch = u"refs/heads/jenkins/{0}-{1}".format(self.branch_name, self.sha[:7])
        return self.github_helper.branch_exists(self.repository, self.branch)

    def _create_new_branch(self):
        LOGGER.info(u"modified files: {}".format(self.modified_files_list))
        commit_sha = self.github_helper.update_list_of_files(
            self.repository,
            self.repo_root,
            self.modified_files_list,
            self.commit_message,
            self.sha,
            self.user.name
        )
        self._create_branch(commit_sha)

    def _create_new_pull_request(self):
        # If there are reviewers to be added, split them into python lists
        if isinstance(self.user_reviewers, (str, six.text_type)) and self.user_reviewers:
            user_reviewers = self.user_reviewers.split(',')
        else:
            user_reviewers = GithubObject.NotSet

        if isinstance(self.team_reviewers, (str, six.text_type)) and self.team_reviewers:
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
            self.pr_body += "\nhttps://github.com/{}/{}/pull/{}".format(self.org, self.repository_name,
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
