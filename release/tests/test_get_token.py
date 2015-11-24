"""
Tests for testeng-ci/release/get-token
"""
from mock import patch, mock_open
from unittest import TestCase

# Ensure we're properly handling python2 vs 3
from sys import version_info
if version_info.major == 2:
    import __builtin__ as builtins  # pylint: disable=import-error
else:
    import builtins  # pylint: disable=import-error

from release.get_token import get_token


class GetTokenTestCase(TestCase):
    """
    TestCase class for loading a github token
    """

    @patch('os.getenv', return_value='abc123')
    def test_token_from_environment(self, _):
        """ Tests that tokens can be read from the environment """
        token = get_token()
        self.assertEqual(token, 'abc123')

    @patch.object(builtins, 'open', new=mock_open(read_data='abc123'))
    def test_token_from_file(self):
        """ Tests that tokens can be read from the a saved file """
        token = get_token()
        self.assertEqual(token, 'abc123')

    @patch.object(builtins, 'raw_input', return_value='abc123')
    def test_token_from_input(self, _):
        """ Tests that tokens can be read from direct user input """
        with patch.object(builtins, 'open', mock_open()):
            token = get_token()
            self.assertEqual(token, 'abc123')
