from __future__ import absolute_import

from unittest import TestCase

from mock import Mock, patch

from jenkins.pull_request_creator import PullRequestCreator


class BokchoyPullRequestTestCase(TestCase):
    """
    Test Case class for upgrade_python_requirements.py
    """

    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.close_existing_pull_requests',
           return_value=[])
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.get_github_instance', return_value=None)
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.connect_to_repo', return_value=None)
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.get_modified_files_list', return_value=None)
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.branch_exists', return_value=None)
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.update_list_of_files', return_value=None)
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.create_pull_request', return_value=None)
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.create_branch', return_value=None)
    @patch('jenkins.pull_request_creator.PullRequestCreator._get_user',
           return_value=Mock(name="fake name", login="fake login"))
    @patch('jenkins.github_helpers.GitHubHelper.delete_branch', return_value=None)
    def test_no_changes(self, delete_branch_mock, get_user_mock, create_branch_mock, create_pr_mock,
                        update_files_mock, branch_exists_mock, modified_list_mock, repo_mock, authenticate_mock,
                        close_existing_prs_mock):
        """
        Ensure a merge with no changes to db files will not result in any updates.
        """
        pull_request_creator = PullRequestCreator('--sha=123', '--repo_root=../../edx-platform', 'upgrade-branch', [],
                                                  [], 'Upgrade python requirements', 'Update python requirements',
                                                  'make upgrade PR', '--org=edx')
        pull_request_creator.create(True)

        assert authenticate_mock.called
        assert repo_mock.called
        assert modified_list_mock.called
        assert not branch_exists_mock.called
        assert not create_branch_mock.called
        assert not update_files_mock.called
        assert not create_pr_mock.called

    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.close_existing_pull_requests',
           return_value=[])
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.get_github_instance',
           return_value=Mock())
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.connect_to_repo', return_value=Mock())
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.get_modified_files_list',
           return_value=["requirements/edx/base.txt", "requirements/edx/coverage.txt"])
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.branch_exists', return_value=False)
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.update_list_of_files', return_value=None)
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.create_pull_request', return_value=None)
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.create_branch', return_value=None)
    @patch('jenkins.pull_request_creator.PullRequestCreator._get_user',
           return_value=Mock(name="fake name", login="fake login"))
    @patch('jenkins.github_helpers.GitHubHelper.delete_branch', return_value=None)
    def test_changes(self, delete_branch_mock, get_user_mock, create_branch_mock, create_pr_mock,
                     update_files_mock, branch_exists_mock, modified_list_mock, repo_mock, authenticate_mock,
                     close_existing_prs_mock):
        """
        Ensure a merge with no changes to db files will not result in any updates.
        """
        pull_request_creator = PullRequestCreator('--sha=123', '--repo_root=../../edx-platform', 'upgrade-branch', [],
                                                  [], 'Upgrade python requirements', 'Update python requirements',
                                                  'make upgrade PR', '--org=edx')
        pull_request_creator.create(True)

        assert branch_exists_mock.called
        assert create_branch_mock.called
        self.assertEqual(create_branch_mock.call_count, 1)
        assert update_files_mock.called
        self.assertEqual(update_files_mock.call_count, 1)
        assert create_pr_mock.called
        assert not delete_branch_mock.called

    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.close_existing_pull_requests',
           return_value=[])
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.get_github_instance', return_value=None)
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.connect_to_repo', return_value=None)
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.get_modified_files_list',
           return_value=["requirements/edx/base.txt", "requirements/edx/coverage.txt"])
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.branch_exists', return_value=True)
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.update_list_of_files', return_value=None)
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.create_pull_request', return_value=None)
    @patch('jenkins.pull_request_creator.PullRequestCreator.github_helper.create_branch', return_value=None)
    @patch('jenkins.pull_request_creator.PullRequestCreator._get_user',
           return_value=Mock(name="fake name", login="fake login"))
    @patch('jenkins.github_helpers.GitHubHelper.delete_branch', return_value=None)
    def test_branch_exists(self, delete_branch_mock, get_user_mock, create_branch_mock, create_pr_mock,
                           update_files_mock, branch_exists_mock, modified_list_mock, repo_mock, authenticate_mock,
                           close_existing_prs_mock):
        """
        Ensure a merge with no changes to db files will not result in any updates.
        """
        pull_request_creator = PullRequestCreator('--sha=123', '--repo_root=../../edx-platform', 'upgrade-branch', [],
                                                  [], 'Upgrade python requirements', 'Update python requirements',
                                                  'make upgrade PR', '--org=edx')
        pull_request_creator.create(True)

        assert branch_exists_mock.called
        assert not create_branch_mock.called
        assert not create_pr_mock.called
        assert not delete_branch_mock.called
