"""
Tests for testeng-ci/travis/build_info
"""
from mock import patch, mock_open, Mock
from testfixtures import LogCapture
from unittest import TestCase

import httpretty
import requests

from travis.build_info import *

# Ensure we're properly handling python2 vs 3
from sys import version_info
if version_info.major == 2:
    import __builtin__ as builtins  # pylint: disable=import-error
else:
    import builtins  # pylint: disable=import-error


class TestTravisBuildRepoInfo(TestCase):
    """
    Test API client for obtaining build information
    """

    def setUp(self):
        self.response_body = """{
          "@type": "repositories",
          "repositories": [
            {
              "name": "foo"
            }, {
              "name": "bar"
            }
          ]
        }
        """

    @httpretty.activate
    def test_get_active_repos(self):
        httpretty.register_uri(
            httpretty.GET,
            BASE_URL + 'v3/owner/foo/repos',
            body=self.response_body,
            status=200,
        )
        repos = get_repos('foo')
        self.assertListEqual(repos, ['foo', 'bar'])

    @httpretty.activate
    def test_bad_repos_response(self):
        httpretty.register_uri(
            httpretty.GET,
            BASE_URL + 'v3/owner/foo/repos',
            body=self.response_body,
            status=404,
        )
        with self.assertRaises(requests.HTTPError):
            get_repos('foo')

    @httpretty.activate
    def test_unparseable_response(self):
        httpretty.register_uri(
            httpretty.GET,
            BASE_URL + 'v3/owner/foo/repos',
            body="""{"repositories": [{"no-name": "no"}]}""",
            )
        with self.assertRaises(KeyError):
            get_repos('foo')


class TestTravisActiveBuildInfo(TestCase):
    """
    Handle responses for queries on a given repo's builds
    """

    def setUp(self):
        self.url_endpoint = BASE_URL + 'repos/foo/bar-repo/builds'

    @httpretty.activate
    def test_good_build_response(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""[{"id": 1, "state": "created"},
                {"id": 2, "state": "started"}]""",
            )
        builds = get_active_builds('foo', 'bar-repo')
        self.assertEqual(2, len(builds))

    @httpretty.activate
    def test_active_finished_mix(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""[{"id": 1, "state": "created"},
                {"id": 2, "state": "finished"}]""",
            )
        builds = get_active_builds('foo', 'bar-repo')
        self.assertEqual(1, len(builds))

    @httpretty.activate
    def test_all_finished(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""[{"id": 1, "state": "finished"},
                {"id": 2, "state": "finished"}]""",
            )
        builds = get_active_builds('foo', 'bar-repo')
        self.assertEqual(0, len(builds))

    @httpretty.activate
    def test_active_build_count(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""[{"id": 1, "state": "started"},
                {"id": 2, "state": "created"}]""",
            )
        builds = get_active_builds('foo', 'bar-repo')
        total_count, started_count = repo_active_build_count(builds)
        self.assertEqual(2, total_count)
        self.assertEqual(1, started_count)

    @httpretty.activate
    def test_only_queued_builds(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""[{"id": 1, "state": "created"},
                {"id": 2, "state": "created"}]""",
            )
        builds = get_active_builds('foo', 'bar-repo')
        total_count, started_count = repo_active_build_count(builds)
        self.assertEqual(2, total_count)
        self.assertEqual(0, started_count)

    def test_no_active_builds(self):
        builds = []
        total_count, started_count = repo_active_build_count(builds)
        self.assertEqual(0, total_count)
        self.assertEqual(0, started_count)


class TestTravisBuildInfoMain(TestCase):
    """
    Test CLI args, etc
    """

    def setUp(self):
        self.org = 'foo'

    @patch(
        'travis.build_info.get_repos', return_value=['bar']
    )
    @patch(
        'travis.build_info.get_active_builds',
        return_value=[{"id": 1, "state": "started"}]
    )
    def test_main(self, mock_repos, mock_builds):
        args = [
            '--org', self.org
        ]
        with LogCapture() as l:
            main(args)
            l.check(
                ('travis.build_info', 'INFO', 'overall_total=1'),
                ('travis.build_info', 'INFO', 'overall_started=1'),
                ('travis.build_info', 'INFO', 'overall_queued=0')
            )

    @patch(
        'travis.build_info.get_repos', return_value=['bar']
    )
    @patch(
        'travis.build_info.get_active_builds',
        return_value=[{"id": 1, "state": "started"}]
    )
    def test_main_debug(self, mock_repos, mock_builds):
        args = [
            '--org', self.org,
            '--log-level', 'debug'
        ]
        with LogCapture() as l:
            main(args)
            l.check(
                ('travis.build_info', 'DEBUG', '--->bar'),
                ('travis.build_info', 'DEBUG', 'total: 1, started: 1'),
                ('travis.build_info', 'DEBUG', '--------'),
                ('travis.build_info', 'INFO', 'overall_total=1'),
                ('travis.build_info', 'INFO', 'overall_started=1'),
                ('travis.build_info', 'INFO', 'overall_queued=0')
            )
