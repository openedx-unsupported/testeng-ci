# pylint: disable=missing-module-docstring
from unittest import TestCase

from mock import patch
from requests.exceptions import HTTPError

from jenkins.tests.helpers import mock_response, sample_data, Pr
from jenkins.job import JenkinsJob


class JenkinsJobTestCase(TestCase):

    """
    TestCase class for testing deduper.py.
    """

    def setUp(self):  # pylint: disable=super-method-not-called
        self.job_url = 'http://localhost:8080/fakejenkins'
        self.user = 'ausername'
        self.api_key = 'apikey'
        self.job = JenkinsJob(self.job_url, self.user, self.api_key)

    def test_get_json_ok(self):
        data = sample_data([Pr('1').dict], [])
        with patch('requests.get', return_value=mock_response(200, data)):
            response = self.job.get_json()
            self.assertEqual(data, response)

    def test_get_json_bad_response(self):
        with patch('requests.get', return_value=mock_response(400)):
            with self.assertRaises(HTTPError):
                self.job.get_json()

    def test_stop_build_ok(self):
        with patch('requests.post', return_value=mock_response(200, '')):
            response = self.job.stop_build('20')
            self.assertTrue(response)

    def test_stop_build_bad_response(self):
        with patch('requests.post', return_value=mock_response(400, '')):
            with self.assertRaises(HTTPError):
                self.job.stop_build('20')

    def test_update_desc_ok(self):
        with patch('requests.post', return_value=mock_response(200, '')):
            response = self.job.update_build_desc('20', 'new description')
            self.assertTrue(response)

    def test_update_desc_bad_response(self):
        with patch('requests.post', return_value=mock_response(400, '')):
            with self.assertRaises(HTTPError):
                self.job.update_build_desc(
                    '20', 'new description')
