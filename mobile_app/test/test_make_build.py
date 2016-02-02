from collections import namedtuple
from unittest import TestCase

from mock import patch
from sys import version_info
if version_info.major == 2:
    import __builtin__ as builtins  # pylint: disable=import-error
else:
    import builtins  # pylint: disable=import-error

from mobile_app import make_build


Input = namedtuple("Input", ["key", "value"])  # pylint: disable=invalid-name


INPUTS = [
    Input(key="CODE_REPO", value="git://code-repo.git"),
    Input(key="CODE_REVISION", value="code-branch"),
    Input(key="CONFIG_REPO", value="git://config-repo.git"),
    Input(key="CONFIG_REVISION", value="config-branch"),
    Input(key="CONFIG_PATH", value="subpath"),
    Input(key=None, value="../build-repo")
]
VALUES = [entry.value for entry in INPUTS]


class MakeBuildTestCase(TestCase):
    """
    Tests for script that asks user for environment variables
    """

    @patch.object(
        builtins,
        'raw_input',
        side_effect=VALUES
    )
    def test_envs_extracted(self, _):
        """
        Tests that all the arguments we pass in end up in the environment for
        building. Or are passed as part of the argument list
        """
        (args, env) = make_build.collect_params()
        for item in INPUTS:
            if item.key:
                self.assertEqual(env[item.key], item.value)
        self.assertTrue("../build-repo" in args)
