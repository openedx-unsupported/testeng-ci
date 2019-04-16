from unittest import TestCase

import click
from click.testing import CliRunner
from mock import MagicMock, Mock, patch

from jenkins.upgrade_python_requirements import main


class BokchoyPullRequestTestCase(TestCase):
    """
    Test Case class for upgrade_python_requirements.py
    """
    # Create the Cli runner to run the main function with click arguments
    runner = CliRunner()

    @patch('jenkins.upgrade_python_requirements.authenticate_with_github',
           return_value=None)
    @patch('jenkins.upgrade_python_requirements.connect_to_repo',
           return_value=None)
    @patch('jenkins.upgrade_python_requirements.get_modified_files_list',
           return_value=None)
    @patch('jenkins.upgrade_python_requirements.branch_exists',
           return_value=False)
    @patch('jenkins.upgrade_python_requirements.create_branch',
           return_value=None)
    @patch('jenkins.upgrade_python_requirements.update_list_of_files',
           return_value=None)
    @patch('jenkins.upgrade_python_requirements.create_pull_request',
           return_value=None)
    @patch('jenkins.github_helpers.delete_branch',
           return_value=None)
    def test_no_changes(
        self, delete_branch_mock, create_pr_mock, create_branch_mock, update_files_mock,
        branch_exists_mock, modified_list_mock, repo_mock, authenticate_mock
    ):
        """
        Ensure a merge with no changes to db files will not result in any updates.
        """
        result = self.runner.invoke(
            main,
            args=['--sha=123', '--repo_root=../../edx-platform', '--org=edx']
        )
        assert not create_branch_mock.called
        assert not update_files_mock.called
        assert not create_pr_mock.called

    @patch('jenkins.upgrade_python_requirements.authenticate_with_github',
           return_value=Mock())
    @patch('jenkins.upgrade_python_requirements.connect_to_repo',
           return_value=Mock())
    @patch('jenkins.upgrade_python_requirements.branch_exists',
           return_value=False)
    @patch('jenkins.upgrade_python_requirements.get_modified_files_list',
           return_value=["requirements/edx/base.txt", "requirements/edx/coverage.txt"])
    @patch('jenkins.upgrade_python_requirements.create_branch',
           return_value=None)
    @patch('jenkins.upgrade_python_requirements.update_list_of_files',
           return_value=None)
    @patch('jenkins.upgrade_python_requirements.close_existing_pull_requests',
           return_value=[])
    @patch('jenkins.upgrade_python_requirements.create_pull_request',
           return_value=None)
    @patch('jenkins.github_helpers.delete_branch',
           return_value=None)
    def test_changes(
        self, delete_branch_mock, create_pr_mock, close_pr_mock, update_file_mock,
        create_branch_mock,  modified_list_mock, branch_exists_mock, repo_mock, authenticate_mock
    ):
        """
        Ensure a merge with changes to db files will result in the proper updates, a new branch, and a PR.
        """
        result = self.runner.invoke(
            main,
            args=['--sha=123', '--repo_root=../../edx-platform', '--org=edx']
        )
        assert create_branch_mock.called
        self.assertEqual(create_branch_mock.call_count, 1)
        assert update_file_mock.called
        self.assertEqual(update_file_mock.call_count, 1)
        assert create_pr_mock.called
        assert not delete_branch_mock.called

    @patch('jenkins.upgrade_python_requirements.authenticate_with_github',
           return_value=None)
    @patch('jenkins.upgrade_python_requirements.connect_to_repo',
           return_value=None)
    @patch('jenkins.upgrade_python_requirements.branch_exists',
           return_value=True)
    @patch('jenkins.upgrade_python_requirements.get_modified_files_list',
           return_value="requirements/edx/base.txt\nrequirements/edx/coverage.txt")
    @patch('jenkins.upgrade_python_requirements.create_branch',
           return_value=None)
    @patch('jenkins.upgrade_python_requirements.create_pull_request',
           return_value=None)
    @patch('jenkins.github_helpers.delete_branch',
           return_value=None)
    def test_branch_exists(
        self, delete_branch_mock, create_pr_mock, create_branch_mock, modified_list_mock,
        get_branch_mock, repo_mock, authenticate_mock
    ):
        """
        If the branch for a given fingerprint already exists, make sure the script
        doesn't try to create a new branch or create a PR.
        """
        result = self.runner.invoke(
            main,
            args=['--sha=123', '--repo_root=../../edx-platform', '--org=edx']
        )
        assert not create_branch_mock.called
        assert not create_pr_mock.called
        assert not delete_branch_mock.called
