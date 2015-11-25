"""
Tests for testeng-ci/release/get-token
"""
from mock import patch, mock_open, Mock
from unittest import TestCase

# Ensure we're properly handling python2 vs 3
from sys import version_info
if version_info.major == 2:
    import __builtin__ as builtins  # pylint: disable=import-error
else:
    import builtins  # pylint: disable=import-error

from release import get_token
from release.github_api import GithubApi, RequestFailed
from release.tests.aborted import Aborted


class GetTokenTestCase(TestCase):
    """
    TestCase class for loading a github token
    """

    @patch.object(get_token, 'validate_token', new=Mock())
    @patch('os.getenv', return_value='abc123')
    def test_token_from_environment(self, _):
        """
        Tests that tokens can be read from the environment
        """
        token = get_token.get_token()
        self.assertEqual(token, 'abc123')

    @patch.object(builtins, 'open', new=mock_open(read_data='abc123'))
    @patch.object(get_token, 'validate_token', new=Mock())
    def test_token_from_file(self):
        """
        Tests that tokens can be read from the saved file
        """
        token = get_token.get_token()
        self.assertEqual(token, 'abc123')

    @patch.object(get_token, 'validate_token', new=Mock())
    @patch('os.getenv', return_value='env-token')
    @patch.object(builtins, 'open', new=mock_open(read_data='file-token'))
    def test_env_takes_precedence(self, _):
        """
        Tests that tokens in the environment take precedence
        over tokens from files
        """
        token = get_token.get_token()
        self.assertEqual(token, 'env-token')

    @patch.object(get_token, 'validate_token', new=Mock())
    @patch.object(builtins, 'raw_input', return_value='abc123')
    def test_token_from_input(self, _):
        """
        Tests that tokens can be read from direct user input
        """
        with patch.object(builtins, 'open', mock_open()):
            token = get_token.get_token()
            self.assertEqual(token, 'abc123')

    @patch('os.getenv', return_value='abc123')
    @patch('sys.exit', new=Mock(side_effect=Aborted))
    def test_validation_fails_unauth(self, _):
        """
        Tests that invalid tokens cause abort.
        """
        def failed_request():
            """
            Helper that causes a failed network request
            """
            mock_response = Mock()
            mock_response.status_code = 401
            raise RequestFailed(mock_response)

        mock = Mock(side_effect=failed_request)
        with patch.object(GithubApi, 'user', mock):
            with self.assertRaises(Aborted):
                _ = get_token.get_token()

    def test_validate_token(self):
        """
        Test that a valid token doesn't cause an error
        """
        with patch.object(GithubApi, 'user'):
            with patch('os.getenv', return_value='abc123'):
                get_token.get_token()
