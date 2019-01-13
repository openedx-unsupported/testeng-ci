"""
Tests for the iOS build launcher script
"""

from mock import patch

from unittest import TestCase

import six

from .. import make_ios_build


class MakeIOSBuildTestCase(TestCase):
    # pylint: disable=missing-docstring

    @patch.object(six.moves, 'input', side_effect="y")
    def test_with_testflight(self, _):
        def verify_build_arguments(trigger_repo, overrides):
            self.assertEqual(
                trigger_repo,
                "git@github.com:edx/edx-app-build-ios.git"
            )
            self.assertEqual(overrides["DISTRIBUTION"], "release")
            self.assertEqual(overrides["CONFIG_PATH"], "prod")

        with patch.object(
            make_ios_build,
            'make_build',
            side_effect=verify_build_arguments
        ):
            make_ios_build.make_ios_build()

    @patch.object(six.moves, 'input', side_effect="n")
    def test_without_testflight(self, _):
        def verify_build_arguments(trigger_repo, overrides):
            self.assertEqual(
                trigger_repo,
                "git@github.com:edx/edx-app-build-ios.git"
            )
            self.assertEqual(overrides["DISTRIBUTION"], "enterprise")
            self.assertEqual(overrides.get("CONFIG_PATH", None), None)
            self.assertEqual(overrides.get("CONFIG_REPO", None), None)

        with patch.object(
            make_ios_build,
            'make_build',
            side_effect=verify_build_arguments
        ):
            make_ios_build.make_ios_build()
