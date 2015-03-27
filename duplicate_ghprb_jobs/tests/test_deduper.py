import json
from time import time
from mock import patch, Mock
from requests import Response
from requests.exceptions import HTTPError
from unittest import TestCase

from duplicate_ghprb_jobs.deduper import (
    GhprbOutdatedBuildAborter,
    append_url,
    deduper_main,
)


def sample_data(running_builds, not_running_builds):
    """
    Args:
        running_builds: (list of str) A list of PR numbers that have
            running builds. For example, ['1', '1', '2'] indicates
            that there are currently 2 builds running for PR #1 and
            1 build running for PR #2. The last instance of '1' in
            the list will correlate to the currently relevant build.
            The build number will be the array index of the item.
        not_running_builds: (list of str) A list of PR numbers that
            have previously run builds. The build number will be the
            array index of the item plus the length of running_builds.
    Returns:
        Python dict of build data. This is in the format expected to
        be returned by the jenkins api.
    """
    builds = []
    first_time = int(time())
    for i in range(0, len(running_builds)):
        builds.append(
            '{"actions" : [{"parameters" :[{"name": "ghprbPullId",'
            '"value" : "' + running_builds[i] + '"}]},{},{}], '
            '"building": true, "number": ' + str(i) +
            ', "timestamp" : ' + str(first_time + i) + '}'
        )

    for i in range(0, len(not_running_builds)):
        builds.append(
            '{"actions" : [{"parameters" :[{"name": "ghprbPullId",'
            '"value" : "' + not_running_builds[i] + '"}]},{},{}], '
            '"building": false, "number": ' + str(i + len(running_builds))
            + ', "timestamp" : ' + str(first_time - i) + '}'
        )

    build_data = ''.join([
        '{"builds": [',
        ','.join(builds),
        ']}',
    ])

    return json.loads(build_data)


def mock_response(status_code, data=None):
    mock_response = Response()
    mock_response.status_code = status_code
    mock_response.json = Mock(return_value=data)
    return mock_response


class DeduperTestCase(TestCase):

    """
    TestCase class for testing deduper.py.
    """

    def setUp(self):
        self.job_url = 'http://localhost:8080/fakejenkins'
        self.user = 'ausername'
        self.api_key = 'apikey'
        self.deduper = GhprbOutdatedBuildAborter(
            self.job_url, self.user, self.api_key)

    def test_append_url(self):
        expected = 'http://my_base_url.com/the_extra_part'
        inputs = [
            ('http://my_base_url.com', 'the_extra_part'),
            ('http://my_base_url.com', '/the_extra_part'),
            ('http://my_base_url.com/', 'the_extra_part'),
            ('http://my_base_url.com/', '/the_extra_part'),
        ]

        for i in inputs:
            returned = append_url(*i)
            self.assertEqual(expected, returned,
                             msg="{e} != {r}\nInputs: {i}".format(
                                 e=expected,
                                 r=returned,
                                 i=str(i)
                             )
                             )

    def test_get_running_builds_3_building(self):
        data = sample_data(['1', '2', '3'], ['4'])
        builds = self.deduper.get_running_builds(data)
        self.assertEqual(len(builds), 3)

    def test_get_running_builds_1_building(self):
        data = sample_data(['4'], ['1', '2', '3'])
        builds = self.deduper.get_running_builds(data)
        self.assertEqual(len(builds), 1)

    def test_get_running_builds_none_building(self):
        data = sample_data([], ['1', '2', '3', '4'])
        builds = self.deduper.get_running_builds(data)
        self.assertEqual(len(builds), 0)

    def test_description(self):
        expected = ("[PR #2] Build automatically aborted because "
                    "there is a newer build for the same PR. See build #1.")
        returned = self.deduper._aborted_description(1, 2)
        self.assertEqual(expected, returned)

    def test_get_json_ok(self):
        data = sample_data(['1'], [])
        with patch('requests.get', return_value=mock_response(200, data)):
            response = self.deduper.get_json()
            self.assertEqual(data, response)

    def test_get_json_bad_response(self):
        with patch('requests.get', return_value=mock_response(400)):
            with self.assertRaises(HTTPError):
                response = self.deduper.get_json()

    def test_stop_build_ok(self):
        with patch('requests.post', return_value=mock_response(200, '')):
            response = self.deduper.stop_build('20')
            self.assertTrue(response)

    def test_stop_build_bad_response(self):
        with patch('requests.post', return_value=mock_response(400, '')):
            with self.assertRaises(HTTPError):
                response = self.deduper.stop_build('20')

    def test_update_desc_ok(self):
        with patch('requests.post', return_value=mock_response(200, '')):
            response = self.deduper.update_build_desc('20', 'new description')
            self.assertTrue(response)

    def test_update_desc_bad_response(self):
        with patch('requests.post', return_value=mock_response(400, '')):
            with self.assertRaises(HTTPError):
                response = self.deduper.update_build_desc(
                    '20', 'new description')

    @patch(
        'duplicate_ghprb_jobs.deduper.GhprbOutdatedBuildAborter.stop_build',
        return_value=True)
    @patch(
        ('duplicate_ghprb_jobs.deduper.GhprbOutdatedBuildAborter.'
         'update_build_desc'),
        return_value=True)
    @patch(
        ('duplicate_ghprb_jobs.deduper.GhprbOutdatedBuildAborter.'
         '_aborted_description'),
        return_value='new description')
    def test_stop_duplicates_with_duplicates(self, mock_desc,
                                             update_desc,
                                             stop_build):
        sample_buid_data = sample_data(['1', '2', '2', '3'], [])
        build_data = self.deduper.get_running_builds(sample_buid_data)
        response = self.deduper.stop_duplicates(build_data)
        stop_build.assert_called_once_with(1)
        update_desc.assert_called_once_with(1, mock_desc())

    @patch(
        'duplicate_ghprb_jobs.deduper.GhprbOutdatedBuildAborter.stop_build',
        side_effect=HTTPError())
    @patch(
        ('duplicate_ghprb_jobs.deduper.GhprbOutdatedBuildAborter.'
         'update_build_desc'),
        return_value=True)
    def test_stop_duplicates_failed_to_stop(self, update_desc, stop_build):
        sample_buid_data = sample_data(['1', '2', '2', '3'], [])
        build_data = self.deduper.get_running_builds(sample_buid_data)
        response = self.deduper.stop_duplicates(build_data)
        stop_build.assert_called_once_with(1)
        self.assertFalse(update_desc.called)

    @patch(
        'duplicate_ghprb_jobs.deduper.GhprbOutdatedBuildAborter.stop_build',
        return_value=True)
    @patch(
        ('duplicate_ghprb_jobs.deduper.GhprbOutdatedBuildAborter.'
         'update_build_desc'),
        return_value=True)
    def test_stop_duplicates_no_duplicates(self, update_desc, stop_build):
        sample_buid_data = sample_data(['1', '2', '3'], ['2'])
        build_data = self.deduper.get_running_builds(sample_buid_data)
        response = self.deduper.stop_duplicates(build_data)
        self.assertFalse(stop_build.called)
        self.assertFalse(update_desc.called)

    @patch(
        'duplicate_ghprb_jobs.deduper.GhprbOutdatedBuildAborter.get_json',
        return_value=sample_data(['1', '2', '2', '3'], ['4', '5', '5']))
    @patch(
        'duplicate_ghprb_jobs.deduper.GhprbOutdatedBuildAborter.stop_build',
        return_value=True)
    @patch(
        ('duplicate_ghprb_jobs.deduper.GhprbOutdatedBuildAborter.'
         'update_build_desc'),
        return_value=True)
    @patch(
        ('duplicate_ghprb_jobs.deduper.GhprbOutdatedBuildAborter.'
         '_aborted_description'),
        return_value='new description')
    def test_main(self, mock_desc, update_desc, stop_build, get_json):
        args = [
            '-t', self.api_key,
            '-u', self.user,
            '-j', self.job_url,
            '--log-level', 'INFO',
        ]

        deduper_main(args)
        get_json.assert_called_once_with()
        stop_build.assert_called_once_with(1)
        update_desc.assert_called_once_with(1, mock_desc())
