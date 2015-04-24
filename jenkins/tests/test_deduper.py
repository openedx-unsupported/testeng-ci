from mock import patch
from requests.exceptions import HTTPError
from unittest import TestCase

from jenkins.tests.helpers import sample_data, Pr
from jenkins.deduper import GhprbOutdatedBuildAborter, deduper_main
from jenkins.job import JenkinsJob


class DeduperTestCase(TestCase):

    """
    TestCase class for testing deduper.py.
    """

    def setUp(self):
        self.job_url = 'http://localhost:8080/fakejenkins'
        self.user = 'ausername'
        self.api_key = 'apikey'
        job = JenkinsJob(self.job_url, self.user, self.api_key)
        self.deduper = GhprbOutdatedBuildAborter(job)

    def test_get_running_builds_3_building(self):
        data = sample_data(
            [Pr('1').dict, Pr('2').dict, Pr('3').dict], [Pr('4').dict])
        builds = self.deduper.get_running_builds(data)
        self.assertEqual(len(builds), 3)

    def test_get_running_builds_1_building(self):
        data = sample_data(
            [Pr('4').dict], [Pr('1').dict, Pr('2').dict, Pr('3').dict])
        builds = self.deduper.get_running_builds(data)
        self.assertEqual(len(builds), 1)

    def test_get_running_builds_none_building(self):
        data = sample_data(
            [], [Pr('1').dict, Pr('2').dict, Pr('3').dict, Pr('4').dict])
        builds = self.deduper.get_running_builds(data)
        self.assertEqual(len(builds), 0)

    def test_description(self):
        expected = ("[PR #2] Build automatically aborted because "
                    "there is a newer build for the same PR. See build #1.")
        returned = self.deduper._aborted_description(1, 2)
        self.assertEqual(expected, returned)

    @patch('jenkins.job.JenkinsJob.stop_build', return_value=True)
    @patch('jenkins.job.JenkinsJob.update_build_desc', return_value=True)
    @patch('jenkins.deduper.GhprbOutdatedBuildAborter._aborted_description',
           return_value='new description')
    def test_stop_duplicates_with_duplicates(self, mock_desc,
                                             update_desc,
                                             stop_build):
        sample_build_data = sample_data(
            [Pr('1').dict, Pr('2').dict, Pr('2').dict, Pr('3').dict], [])
        build_data = self.deduper.get_running_builds(sample_build_data)
        self.deduper.stop_duplicates(build_data)
        stop_build.assert_called_once_with(2)
        update_desc.assert_called_once_with(2, mock_desc())

    @patch('jenkins.job.JenkinsJob.stop_build', side_effect=HTTPError())
    @patch('jenkins.job.JenkinsJob.update_build_desc', return_value=True)
    def test_stop_duplicates_failed_to_stop(self, update_desc, stop_build):
        sample_build_data = sample_data(
            [Pr('1').dict, Pr('2').dict, Pr('2').dict, Pr('3').dict], [])
        build_data = self.deduper.get_running_builds(sample_build_data)
        self.deduper.stop_duplicates(build_data)
        stop_build.assert_called_once_with(2)
        self.assertFalse(update_desc.called)

    @patch('jenkins.job.JenkinsJob.stop_build', return_value=True)
    @patch('jenkins.job.JenkinsJob.update_build_desc', return_value=True)
    def test_stop_duplicates_no_duplicates(self, update_desc, stop_build):
        sample_build_data = sample_data(
            [Pr('1').dict, Pr('2').dict, Pr('3').dict], [Pr('2').dict])
        build_data = self.deduper.get_running_builds(sample_build_data)
        self.deduper.stop_duplicates(build_data)
        self.assertFalse(stop_build.called)
        self.assertFalse(update_desc.called)

    @patch('jenkins.job.JenkinsJob.get_json', return_value=sample_data(
        [Pr('1').dict, Pr('2', author='a').dict, Pr('2', author='b').dict],
        [Pr('4').dict, Pr('5').dict, Pr('5').dict]))
    @patch('jenkins.job.JenkinsJob.stop_build', return_value=True)
    @patch('jenkins.job.JenkinsJob.update_build_desc', return_value=True)
    @patch('jenkins.deduper.GhprbOutdatedBuildAborter._aborted_description',
           return_value='new description')
    def test_main_default_per_author(
            self, mock_desc, update_desc, stop_build, get_json):
        args = [
            '-t', self.api_key,
            '-u', self.user,
            '-j', self.job_url,
            '--log-level', 'INFO',
        ]
        deduper_main(args)
        get_json.assert_called_once_with()
        stop_build.assert_called_once_with(2)
        update_desc.assert_called_once_with(2, mock_desc())

    @patch('jenkins.job.JenkinsJob.get_json', return_value=sample_data(
        [Pr('1').dict, Pr('2', author='a').dict, Pr('2', author='b').dict],
        [Pr('4').dict, Pr('5').dict, Pr('5').dict]))
    @patch('jenkins.job.JenkinsJob.stop_build', return_value=True)
    @patch('jenkins.job.JenkinsJob.update_build_desc', return_value=True)
    def test_main_one_per_author(self, update_desc, stop_build, get_json):
        args = [
            '-t', self.api_key,
            '-u', self.user,
            '-j', self.job_url,
            '--log-level', 'INFO',
            '--one-per-author'
        ]
        deduper_main(args)
        get_json.assert_called_once_with()
        self.assertFalse(stop_build.called)
        self.assertFalse(update_desc.called)


class DedupePerAuthorTestCase(TestCase):

    """
    TestCase class for testing the one_per_author feature
    """

    def setUp(self):
        self.job_url = 'http://localhost:8080/fakejenkins'
        self.user = 'ausername'
        self.api_key = 'apikey'
        job = JenkinsJob(self.job_url, self.user, self.api_key)
        self.deduper = GhprbOutdatedBuildAborter(job, one_per_author=True)

    @patch('jenkins.job.JenkinsJob.stop_build', return_value=True)
    @patch('jenkins.job.JenkinsJob.update_build_desc', return_value=True)
    def test_stop_per_author_no_duplicates(self, update_desc, stop_build):
        sample_build_data = sample_data(
            [Pr('2', author='foo').dict, Pr('2', author='bar').dict], [])
        build_data = self.deduper.get_running_builds(sample_build_data)
        self.deduper.stop_duplicates(build_data)
        self.assertFalse(stop_build.called)

    @patch('jenkins.job.JenkinsJob.stop_build', return_value=True)
    @patch('jenkins.job.JenkinsJob.update_build_desc', return_value=True)
    def test_stop_per_author_no_duplicates_by_pr(self, update_desc,
                                                 stop_build):
        sample_build_data = sample_data(
            [Pr('2', author='foo').dict, Pr('3', author='foo').dict], [])
        build_data = self.deduper.get_running_builds(sample_build_data)
        self.deduper.stop_duplicates(build_data)
        self.assertFalse(stop_build.called)

    @patch('jenkins.job.JenkinsJob.stop_build', return_value=True)
    @patch('jenkins.job.JenkinsJob.update_build_desc', return_value=True)
    def test_stop_per_author_with_duplicates(self, update_desc, stop_build):
        sample_build_data = sample_data(
            [Pr('2', author='foo').dict, Pr('2', author='foo').dict], [])
        build_data = self.deduper.get_running_builds(sample_build_data)
        self.deduper.stop_duplicates(build_data)
        stop_build.assert_called_once_with(1)
