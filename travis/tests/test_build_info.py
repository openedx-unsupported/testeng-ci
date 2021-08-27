"""
Tests for testeng-ci/travis/build_info
"""

import os
from unittest import TestCase
from unittest.mock import patch

import httpretty
import requests
from ddt import data, ddt
from testfixtures import LogCapture

from travis.build_info import (BASE_URL, active_job_counts, get_active_jobs,
                               get_average_build_duration, get_builds,
                               get_last_n_successful_builds, get_repos, main,
                               repo_active_build_count)


class TestTravisBuildRepoInfo(TestCase):
    """
    Test API client for obtaining build information
    """

    def setUp(self):
        super().setUp()
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
        super().setUp()
        self.url_endpoint = BASE_URL + 'repos/foo/bar-repo/builds'

    @httpretty.activate
    def test_good_build_response(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""[{"id": 1, "state": "created"},
                {"id": 2, "state": "started"}]""",
        )
        builds = get_builds('foo', 'bar-repo')
        self.assertEqual(2, len(builds))

    @httpretty.activate
    def test_active_finished_mix(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""[{"id": 1, "state": "created"},
                {"id": 2, "state": "finished"}]""",
        )
        builds = get_builds('foo', 'bar-repo')
        self.assertEqual(1, len(builds))

    @httpretty.activate
    def test_all_finished(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""[{"id": 1, "state": "finished"},
                {"id": 2, "state": "finished"}]""",
        )
        builds = get_builds('foo', 'bar-repo')
        self.assertEqual(0, len(builds))

    @httpretty.activate
    def test_active_build_count(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""[{"id": 1, "state": "started"},
                {"id": 2, "state": "created"}]""",
        )
        builds = get_builds('foo', 'bar-repo')
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
        builds = get_builds('foo', 'bar-repo')
        total_count, started_count = repo_active_build_count(builds)
        self.assertEqual(2, total_count)
        self.assertEqual(0, started_count)

    def test_no_active_builds(self):
        builds = []
        total_count, started_count = repo_active_build_count(builds)
        self.assertEqual(0, total_count)
        self.assertEqual(0, started_count)


class TestTravisFinishedBuildInfo(TestCase):
    """
    Handle responses for queries on a given repo's builds
    """

    def setUp(self):
        super().setUp()
        self.url_endpoint = BASE_URL + 'repos/foo/bar-repo/builds'

    @httpretty.activate
    def test_vanilla_finished_builds(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""[{"id": 1, "state": "finished"},
                {"id": 2, "state": "finished"}]""",
        )
        builds = get_builds('foo', 'bar-repo', is_finished=True)
        self.assertEqual(2, len(builds))

    @httpretty.activate
    def test_active_finished_mix(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""[{"id": 1, "state": "created"},
                {"id": 2, "state": "finished"},
                {"id": 3, "state": "started"}]""",
        )
        builds = get_builds('foo', 'bar-repo', is_finished=True)
        self.assertEqual(1, len(builds))

    @httpretty.activate
    def test_all_finished(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""[{"id": 1, "state": "finished"},
                {"id": 2, "state": "finished"}]""",
        )
        builds = get_builds('foo', 'bar-repo', is_finished=True)
        self.assertEqual(2, len(builds))

    @httpretty.activate
    def test_all_finished_but_asking_for_active(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""[{"id": 1, "state": "finished"},
                {"id": 2, "state": "finished"}]""",
        )
        builds = get_builds('foo', 'bar-repo')
        self.assertEqual(0, len(builds))

    @httpretty.activate
    def test_all_active(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""[{"id": 1, "state": "started"},
                {"id": 2, "state": "created"}]""",
        )
        builds = get_builds('foo', 'bar-repo')
        self.assertEqual(2, len(builds))


class TestTravisBuildInfoJobs(TestCase):
    """
    Ensure we can get jobs data
    """

    def setUp(self):
        super().setUp()
        self.url_endpoint = BASE_URL + 'v3/build/11122/jobs'

    @httpretty.activate
    def test_jobs_count(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""
                {"jobs":
                    [
                        {"id": 1, "state": "received"},
                        {"id": 2, "state": "created"}
                    ]
                }
                """,
        )
        jobs = get_active_jobs(11122)
        expected_job_list = [
            {'id': 1, 'state': 'received'},
            {'id': 2, 'state': 'created'}
        ]
        self.assertListEqual(expected_job_list, jobs)

    @httpretty.activate
    def test_jobs_count_with_completed(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""
                {"jobs":
                    [
                        {"id": 1, "state": "passed"},
                        {"id": 2, "state": "created"},
                        {"id": 3, "state": "failed"}
                    ]
                }
                """,
        )
        jobs = get_active_jobs(11122)
        self.assertEqual(1, len(jobs))

    @httpretty.activate
    def test_jobs_count_no_active(self):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body="""
                {"jobs":
                    [
                        {"id": 1, "state": "passed"},
                        {"id": 2, "state": "passed"},
                        {"id": 3, "state": "failed"}
                    ]
                }
                """,
        )
        jobs = get_active_jobs(11122)
        self.assertEqual(0, len(jobs))

    def test_active_job_counts_zero_builds(self):
        job_count, started_jobs_count = active_job_counts([])
        self.assertTupleEqual((0, 0), (job_count, started_jobs_count))

    def test_active_job_counts_some(self):
        jobs_list = [
            {"id": 1, "state": "queued"},
            {"id": 1, "state": "started"},
        ]
        job_count, started_jobs_count = active_job_counts(jobs_list)
        self.assertEqual(2, job_count)
        self.assertEqual(1, started_jobs_count)

    def test_active_job_counts_various(self):
        jobs_list = [
            {"id": 1, "state": "queued"},
            {"id": 1, "state": "created"},
            {"id": 1, "state": "received"},
        ]
        job_count, started_jobs_count = active_job_counts(jobs_list)
        self.assertEqual(3, job_count)
        self.assertEqual(0, started_jobs_count)

    def test_active_job_counts_mult(self):
        jobs_list = [
            {"id": 1, "state": "queued"},
            {"id": 1, "state": "started"},
            {"id": 1, "state": "started"},
        ]
        job_count, started_jobs_count = active_job_counts(jobs_list)
        self.assertEqual(3, job_count)
        self.assertEqual(2, started_jobs_count)


@ddt
class TestTravisSuccessfulBuilds(TestCase):
    """
    Test successful build data capture
    """

    def setUp(self):
        super().setUp()
        self.url_endpoint = BASE_URL + 'repos/foo/bar-repo/builds'

    @data(
        {"requested": 5, "expected": 5},
        {"requested": 7, "expected": 6},  # the max found in the file is 6

    )
    @httpretty.activate
    def test_successful_builds(self, test_data):
        httpretty.register_uri(
            httpretty.GET,
            self.url_endpoint,
            body=self._load_mock_builds_response_file(
                "fixtures/builds_response.list"
            ),
        )

        successful_builds = get_last_n_successful_builds(
            'foo',
            'bar-repo',
            test_data['requested']
        )
        self.assertEqual(len(successful_builds), test_data['expected'])

    def _load_mock_builds_response_file(self, filename):
        """
        returns the contents of the specified text fixture/file
        """
        test_dir = os.path.dirname(__file__)
        abs_file = os.path.join(test_dir, filename)
        with open(abs_file, encoding='utf-8') as test_file:
            contents = test_file.read()

        return contents


class TestBuildDurationCalculation(TestCase):
    """
    test build duration calculation, such as average
      build duration
    """

    def test_average_build_duration_returns_minutes(self):
        builds = [
            {'id': 1, 'duration': 60}
        ]
        self.assertEqual(get_average_build_duration(builds), 1)

    def test_average_duration_whole_numbers(self):
        """
        Average number would give a float, but the method
        returns a whole number
        """
        builds = [
            {'id': 1, 'duration': 600},
            {'id': 2, 'duration': 600},
            {'id': 3, 'duration': 660}
        ]
        self.assertEqual(get_average_build_duration(builds), 10)


class TestTravisBuildInfoMain(TestCase):
    """
    Test CLI args, and output, output formatting, etc
    """

    def setUp(self):
        super().setUp()
        self.org = 'foo'
        self.mock_repos = patch(
            'travis.build_info.get_repos', return_value=['bar']
        )
        self.mock_builds = patch(
            'travis.build_info.get_builds',
            return_value=[{"id": 1, "state": "started"}]
        )
        self.mock_jobs = patch(
            'travis.build_info.get_active_jobs',
            return_value=[
                {"id": 1, "state": "passed"},
                {"id": 2, "state": "passed"},
                {"id": 3, "state": "failed"}
            ]

        )

        self.mock_repos.start()
        self.mock_builds.start()
        self.mock_jobs.start()
        self.addCleanup(patch.stopall)

    def test_main(self):
        args = [
            '--org', self.org
        ]
        with LogCapture() as log_capture:
            main(args)
            log_capture.check(
                ('travis.build_info', 'INFO', 'overall_total=1'),
                ('travis.build_info', 'INFO', 'overall_started=1'),
                ('travis.build_info', 'INFO', 'overall_queued=0')
            )

    def test_main_build_opt_in(self):
        args = [
            '--org', self.org,
            '--task-class', 'build'
        ]
        with LogCapture() as log_capture:
            main(args)
            log_capture.check(
                ('travis.build_info', 'INFO', 'overall_total=1'),
                ('travis.build_info', 'INFO', 'overall_started=1'),
                ('travis.build_info', 'INFO', 'overall_queued=0')
            )

    @patch(
        'travis.build_info.get_builds',
        return_value=[
            {
                "id": 1,
                "state": "finished",
                "result": 0,
                "number": 10,
                "duration": 600
            }
        ]
    )
    def test_main_duration(self, _mock_builds):
        args = [
            '--org', self.org,
            '--task-class', 'duration'
        ]
        with LogCapture() as log_capture:
            main(args)
            log_capture.check(
                (
                    'travis.build_info',
                    'INFO',
                    "[{'repo': 'bar', 'average duration': 10}]"
                )
            )

    def test_main_debug(self):
        args = [
            '--org', self.org,
            '--log-level', 'debug'
        ]
        with LogCapture() as log_capture:
            main(args)
            log_capture.check(
                ('travis.build_info', 'DEBUG', '--->bar'),
                ('travis.build_info', 'DEBUG', 'total: 1, started: 1'),
                ('travis.build_info', 'DEBUG', '--------'),
                ('travis.build_info', 'INFO', 'overall_total=1'),
                ('travis.build_info', 'INFO', 'overall_started=1'),
                ('travis.build_info', 'INFO', 'overall_queued=0')
            )

    def test_main_debug_jobs(self):
        args = [
            '--org', self.org,
            '--log-level', 'debug',
            '--task-class', 'job'
        ]

        with LogCapture() as log_capture:
            main(args)
            log_capture.check(
                ('travis.build_info', 'DEBUG', '----> bar'),
                ('travis.build_info', 'DEBUG',
                 'total jobs: 3, started jobs: 0'),
                ('travis.build_info', 'DEBUG', '--------'),
                ('travis.build_info', 'INFO', 'overall_jobs_total=3'),
                ('travis.build_info', 'INFO', 'overall_jobs_started=0')
            )
