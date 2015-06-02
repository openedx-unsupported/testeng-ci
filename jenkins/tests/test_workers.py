"""
Tests for testeng-ci/jenkins/workers.py.
"""
import logging
from helpers import mock_response
from jenkins.workers import get_queue_data, get_computer_data, main
from mock import patch
from testfixtures import LogCapture
from unittest import TestCase

sample_comp_data = {
    "busyExecutors": 28,
    "totalExecutors": 38,
    'computer': [{
        'offline': False,
        'displayName': 'worker-tag (i-abcd1234)',
        'numExecutors': '1',
    }],
}

sample_q_data = {"items": [{}, {}, {}, ]}

expected_comp_data = [
    'busy_executors_jenkins=28',
    'total_executors_jenkins=38',
    'worker-tag_count=1'
]
expected_q_data = ['queue_length=3']


class JenkinsWorkersTestCase(TestCase):
    """
    TestCase class for testing workers.py.
    """

    def setUp(self):
        self.jenkins_url = 'http://localhost:8080/fakejenkins'

    @patch('jenkins.workers.get_queue_data', return_value=expected_q_data)
    @patch(
        'jenkins.workers.get_computer_data',
        return_value=expected_comp_data
    )
    def test_workers_main(self, mock_get_queue_data, mock_get_computer_data):
        expected_output = ['datasrc=jenkins, jenkins_master=localhost:8080']
        expected_output.extend(expected_q_data)
        expected_output.extend(expected_comp_data)
        expected_output = ', '.join(expected_output)

        with LogCapture() as l:
            args = ['-j', self.jenkins_url]
            main(args)
            mock_get_queue_data.assert_called_once_with(self.jenkins_url)
            mock_get_computer_data.assert_called_once_with(self.jenkins_url)
            output = ('jenkins.workers', 'INFO', expected_output)
            l.check(output)

    @patch('requests.get', return_value=mock_response(200, sample_q_data))
    def test_get_queue_data(self, mock_requests):
        fields = get_queue_data(self.jenkins_url)
        mock_requests.assert_called_once()
        self.assertEqual(fields, expected_q_data)

    @patch('requests.get', return_value=mock_response(200, sample_comp_data))
    def test_get_computer_data(self, mock_requests):
        fields = get_computer_data(self.jenkins_url)
        mock_requests.assert_called_once()
        self.assertEqual(fields, expected_comp_data)
