# pylint: disable=missing-module-docstring
from unittest import TestCase

from mock import patch, call
from requests.exceptions import HTTPError

from jenkins.tests.helpers import sample_data, mock_utcnow, Pr
from jenkins.timeout import BuildTimeout, timeout_main
from jenkins.job import JenkinsJob


class TimeoutTestCase(TestCase):

    """
    TestCase class for testing timeout.py.
    """

    def setUp(self):  # pylint: disable=super-method-not-called
        self.job_url = 'http://localhost:8080/fakejenkins'
        self.user = 'ausername'
        self.api_key = 'apikey'
        job = JenkinsJob(self.job_url, self.user, self.api_key)
        self.timer = BuildTimeout(job, 2)

    @mock_utcnow
    def test_get_stuck_builds_3_building(self):
        data = sample_data(
            [Pr('1').dict, Pr('2').dict, Pr('3').dict], [Pr('4').dict])
        builds = self.timer.get_stuck_builds(data)
        self.assertEqual(len(builds), 1)

    @mock_utcnow
    def test_get_stuck_builds_1_building(self):
        data = sample_data(
            [Pr('4').dict], [Pr('1').dict, Pr('2').dict, Pr('3').dict])
        builds = self.timer.get_stuck_builds(data)
        self.assertEqual(len(builds), 0)

    @mock_utcnow
    def test_get_stuck_builds_none_building(self):
        data = sample_data(
            [], [Pr('1').dict, Pr('2').dict, Pr('3').dict, Pr('4').dict])
        builds = self.timer.get_stuck_builds(data)
        self.assertEqual(len(builds), 0)

    @mock_utcnow
    def test_description(self):
        expected = ("Build #1 automatically aborted because it has "
                    "exceeded the timeout of 3 minutes.")
        returned = self.timer._aborted_description(3, 1)  # pylint: disable=protected-access
        self.assertEqual(expected, returned)

    @mock_utcnow
    @patch('jenkins.job.JenkinsJob.stop_build', return_value=True)
    @patch('jenkins.job.JenkinsJob.update_build_desc', return_value=True)
    @patch('jenkins.timeout.BuildTimeout._aborted_description',
           return_value='new description')
    def test_stop_stuck_builds_with_stuck(self, mock_desc,
                                          update_desc,
                                          stop_build):
        sample_build_data = sample_data(
            [Pr('0').dict, Pr('1').dict, Pr('2').dict, Pr('3').dict], [])
        build_data = self.timer.get_stuck_builds(sample_build_data)
        self.timer.stop_stuck_builds(build_data)

        stop_build.assert_has_calls([call(3), call(2)], any_order=True)

        update_desc.assert_has_calls(
            [call(2, mock_desc()), call(3, mock_desc())],
            any_order=True
        )

    @mock_utcnow
    @patch('jenkins.job.JenkinsJob.stop_build', side_effect=HTTPError())
    @patch('jenkins.job.JenkinsJob.update_build_desc', return_value=True)
    def test_stop_stuck_builds_failed_to_stop(self, update_desc, stop_build):
        sample_build_data = sample_data(
            [Pr('1').dict, Pr('2').dict, Pr('3').dict], [])
        build_data = self.timer.get_stuck_builds(sample_build_data)
        self.timer.stop_stuck_builds(build_data)
        stop_build.assert_called_once_with(2)
        self.assertFalse(update_desc.called)

    @mock_utcnow
    @patch('jenkins.job.JenkinsJob.stop_build', return_value=True)
    @patch('jenkins.job.JenkinsJob.update_build_desc', return_value=True)
    def test_stop_stuck_builds_none_stuck(self, update_desc, stop_build):
        sample_build_data = sample_data(
            [Pr('1').dict, Pr('2').dict], [Pr('2').dict])
        build_data = self.timer.get_stuck_builds(sample_build_data)
        self.timer.stop_stuck_builds(build_data)
        self.assertFalse(stop_build.called)
        self.assertFalse(update_desc.called)

    @mock_utcnow
    @patch('jenkins.job.JenkinsJob.get_json', return_value=sample_data(
        [Pr('1').dict, Pr('2').dict, Pr('2').dict],
        [Pr('4').dict, Pr('5').dict, Pr('5').dict]))
    @patch('jenkins.job.JenkinsJob.stop_build', return_value=True)
    @patch('jenkins.job.JenkinsJob.update_build_desc', return_value=True)
    @patch('jenkins.timeout.BuildTimeout._aborted_description',
           return_value='new description')
    def test_main(self, mock_desc, update_desc, stop_build, get_json):
        args = [
            '-t', self.api_key,
            '-u', self.user,
            '-j', self.job_url,
            '--log-level', 'INFO',
            '--timeout', '2',
        ]

        timeout_main(args)
        get_json.assert_called_once_with()
        stop_build.assert_called_once_with(2)
        update_desc.assert_called_once_with(2, mock_desc())
