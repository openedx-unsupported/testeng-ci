"""
Tests for testeng-ci/jenkins/workers.py.
"""
import logging
from helpers import mock_response
from jenkins.workers import log_queue_length, log_worker_counts, main
from mock import patch
from testfixtures import LogCapture
from unittest import TestCase

sample_comp_data = {
    "busyExecutors": 28,
    "totalExecutors": 38
}

sample_q_data = {"items": [{}, {}, {}, ]}


class JenkinsQueueTestCase(TestCase):

    """
    TestCase class for testing workers.py.
    """

    def setUp(self):
        self.jenkins_url = 'http://localhost:8080/fakejenkins'

    @patch('jenkins.workers.log_queue_length')
    @patch('jenkins.workers.log_worker_counts')
    def test_queue_main(self, mock_log_queue_length, mock_log_worker_counts):
        args = ['-j', self.jenkins_url]
        main(args)
        mock_log_queue_length.assert_called_once_with(self.jenkins_url)
        mock_log_worker_counts.assert_called_once_with(self.jenkins_url)

    @patch('requests.get', return_value=mock_response(200, sample_q_data))
    def test_log_queue_length(self, mock_requests):
        with LogCapture() as l:
            instances_1 = log_queue_length(self.jenkins_url)
            mock_requests.assert_called_once()
            output = ('jenkins.workers', 'INFO', 'Build Queue Length: 3')
            l.check(output)

    @patch('requests.get', return_value=mock_response(200, sample_comp_data))
    def test_log_worker_counts(self, mock_requests):
        with LogCapture() as l:
            instances_1 = log_worker_counts(self.jenkins_url)
            mock_requests.assert_called_once()
            line1 = ('jenkins.workers', 'INFO', 'Busy Executors: 28')
            line2 = ('jenkins.workers', 'INFO', 'Total Executors: 38')
            l.check(line1, line2)
