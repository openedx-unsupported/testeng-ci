# pylint: disable=missing-module-docstring,missing-class-docstring
from unittest import TestCase
from unittest.mock import MagicMock, Mock, mock_open, patch

from jenkins.github_helpers import GitHubHelper


class HelpersTestCase(TestCase):

    def test_close_existing_pull_requests(self):
        """
        Make sure we close only PR's by the correct author.
        """

        incorrect_pr_one = Mock()
        incorrect_pr_one.user.name = "Not John"
        incorrect_pr_one.user.login = "notJohn"
        incorrect_pr_one.number = 1
        incorrect_pr_one.head.ref = "incorrect-branch-name"
        incorrect_pr_one.base.ref = "master"

        incorrect_pr_two = Mock()
        incorrect_pr_two.user.name = "John Smith"
        incorrect_pr_two.user.login = "johnsmithiscool100"
        incorrect_pr_two.number = 2
        incorrect_pr_two.head.ref = "incorrect-branch-name-2"
        incorrect_pr_two.base.ref = "master"

        incorrect_pr_three = Mock()
        incorrect_pr_three.user.name = "John Smith"
        incorrect_pr_three.user.login = "fakeuser100"
        incorrect_pr_three.number = 5
        incorrect_pr_three.head.ref = "jenkins/upgrade-python-requirements-ce0515e"
        incorrect_pr_three.base.ref = "some-other-branch"

        correct_pr_one = Mock()
        correct_pr_one.user.name = "John Smith"
        correct_pr_one.user.login = "fakeuser100"
        correct_pr_one.number = 3
        correct_pr_one.head.ref = "jenkins/upgrade-python-requirements-ce0515e"
        correct_pr_one.base.ref = "master"

        correct_pr_two = Mock()
        correct_pr_two.user.name = "John Smith"
        correct_pr_two.user.login = "fakeuser100"
        correct_pr_two.number = 4
        correct_pr_two.head.ref = "jenkins/upgrade-python-requirements-0c51f37"
        correct_pr_two.base.ref = "master"

        mock_repo = Mock()
        mock_repo.get_pulls = MagicMock(return_value=[
            incorrect_pr_one,
            incorrect_pr_two,
            incorrect_pr_three,
            correct_pr_one,
            correct_pr_two
        ])

        deleted_pulls = GitHubHelper().close_existing_pull_requests(mock_repo, "fakeuser100", "John Smith")
        assert deleted_pulls == [3, 4]
        assert not incorrect_pr_one.edit.called
        assert not incorrect_pr_two.edit.called
        assert not incorrect_pr_three.edit.called
        assert correct_pr_one.edit.called
        assert correct_pr_two.edit.called

    def test_get_modified_files_list_no_change(self):
        git_instance = Mock()
        git_instance.ls_files = MagicMock(return_value="")
        with patch('jenkins.github_helpers.Git', return_value=git_instance):
            result = GitHubHelper().get_modified_files_list("edx-platform")
            assert result == []

    def test_get_modified_files_list_with_changes(self):
        git_instance = Mock()
        git_instance.ls_files = MagicMock(return_value="file1\nfile2")
        with patch('jenkins.github_helpers.Git', return_value=git_instance):
            result = GitHubHelper().get_modified_files_list("edx-platform")
            assert result == ["file1", "file2"]

    def test_update_list_of_files_no_change(self):
        repo_mock = Mock()
        repo_root = "../../edx-platform"
        file_path_list = []
        commit_message = "commit"
        sha = "abc123"
        username = "fakeusername100"

        return_sha = GitHubHelper().update_list_of_files(repo_mock, repo_root, file_path_list, commit_message, sha,
                                                         username)
        assert return_sha is None
        assert not repo_mock.create_git_tree.called
        assert not repo_mock.create_git_commit.called

    @patch('jenkins.github_helpers.GitHubHelper.get_file_contents',
           return_value=None)
    @patch('jenkins.github_helpers.InputGitAuthor',
           return_value=Mock())
    @patch('jenkins.github_helpers.InputGitTreeElement',
           return_value=Mock())
    # pylint: disable=unused-argument
    def test_update_list_of_files_with_changes(self, get_file_contents_mock, author_mock,
                                               git_tree_mock):
        # pylint: enable=unused-argument
        repo_mock = Mock()
        repo_root = "../../edx-platform"
        file_path_list = ["path/to/file1", "path/to/file2"]
        commit_message = "commit"
        sha = "abc123"
        username = "fakeusername100"

        return_sha = GitHubHelper().update_list_of_files(repo_mock, repo_root, file_path_list, commit_message, sha,
                                                         username)
        assert repo_mock.create_git_tree.called
        assert repo_mock.create_git_commit.called
        assert return_sha is not None

    def test_get_file_contents(self):
        with patch("builtins.open", mock_open(read_data="data")) as mock_file:
            contents = GitHubHelper().get_file_contents("../../edx-platform", "path/to/file")
            mock_file.assert_called_with("../../edx-platform/path/to/file", "r", encoding='utf-8')
            assert contents == "data"
