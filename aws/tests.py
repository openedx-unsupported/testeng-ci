"""
Tests for testeng-ci/aws.
"""
import boto
import logging
from aws.get_running_instances import get_running_instances, main
from mock import patch
from moto import mock_ec2
from testfixtures import LogCapture
from unittest import TestCase


class GetRunningEC2InstancesTestCase(TestCase):
    """
    TestCase class for testing get_running_instances.py.
    """

    def setUp(self):
        self.key_name = 'some-key-name'
        self.key_name_2 = 'some-key-name-2'
        self.key_id = 'my-key-id'
        self.secret_key = 'my-secret-key'

    @patch('aws.get_running_instances.get_running_instances')
    def test_main(self, mock_get_running_instances):
        args = [
            '-k', self.key_name,
            '-i', self.key_id,
            '-s', self.secret_key,
            '--log-level', 'INFO',
        ]

        main(args)
        mock_get_running_instances.assert_called_once_with(
            self.key_name, self.key_id, self.secret_key
        )

    @mock_ec2
    def test_get_running_instances(self):
        # Open mocked ec2 connection
        conn = boto.connect_ec2(self.key_id, self.secret_key)

        # Add an instance with other self.key_name to mocked ec2
        conn.run_instances('ami-1234abcd', key_name=self.key_name)

        # Add an instance with self.key_name_2 to mocked ec2
        conn.run_instances('ami-1234abcd', key_name=self.key_name_2)
        conn.run_instances('ami-1234abcd', key_name=self.key_name_2)


        # Check that when searching for self.key_name, we count only 1
        # and confirm that the result is logged at INFO level.
        with LogCapture() as l:
            instances_1 = get_running_instances(
                self.key_name, self.key_id, self.secret_key
            )
            self.assertEqual(instances_1, 1)
            expected_log = ('aws.get_running_instances', 'INFO',
                'Number of some-key-name instances on EC2: 1')
            l.check(expected_log)

        # Check that when searching for self.key_name_2, we count only 2
        # and confirm that the result is logged at INFO level
        with LogCapture() as l:
            instances_2 = get_running_instances(
                self.key_name_2, self.key_id, self.secret_key
            )
            self.assertEqual(instances_2, 2)
            expected_log = ('aws.get_running_instances', 'INFO',
                'Number of some-key-name-2 instances on EC2: 2')
            l.check(expected_log)
