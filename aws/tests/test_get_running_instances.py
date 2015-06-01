"""
Tests for testeng-ci/aws.
"""
import boto
import logging
from aws.get_running_instances import get_running_instance_count, main
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

    @patch(
        'aws.get_running_instances.get_running_instance_count',
        return_value=[['mock-field-a=1', 'mock-field-b=2']]
    )
    def test_main(self, mock_get_running_instance_count):
        args = [
            '-k', self.key_name,
            '-i', self.key_id,
            '-s', self.secret_key,
            '--log-level', 'INFO',
        ]

        with LogCapture() as l:
            main(args)
            mock_get_running_instance_count.assert_called_once_with(
                self.key_name, self.key_id, self.secret_key
            )
            output = (
                'aws.get_running_instances',
                'INFO',
                'mock-field-a=1, mock-field-b=2'
            )
            l.check(output)

    @mock_ec2
    def test_get_running_instances(self):
        # Open mocked ec2 connection
        conn = boto.connect_ec2(self.key_id, self.secret_key)

        # Add an instance with other self.key_name to mocked ec2
        conn.run_instances('ami-1234abcd', key_name=self.key_name)

        # Add an instance with self.key_name_2 to mocked ec2
        for i in range(0, 2):
            res = conn.run_instances('ami-1234abcd', key_name=self.key_name_2)
            for inst in res.instances:
                inst.add_tag('worker', 'tag-' + str(i))
                inst.add_tag('master', 'master-' + str(i))

        # Check that when searching for self.key_name, we count only 1
        # for each field.
        expected_data = [
            [
                'datasrc=aws',
                'jenkins_master=untagged',
                'total_executors_jenkins=1',
                'total_executors_ec2=1',
                'untagged-worker_count=1',
            ],
        ]
        actual_data = get_running_instance_count(
            self.key_name, self.key_id, self.secret_key
        )
        self.assertEqual(actual_data, expected_data)

        # Check that when searching for self.key_name, we count count two
        # master tags, a total of 2 instances, and 1 of each worker tag.
        expected_data = sorted([
            [
                'datasrc=aws',
                'jenkins_master=master-0',
                'total_executors_jenkins=1',
                'total_executors_ec2=2',
                'tag-0-worker_count=1',
            ],
            [
                'datasrc=aws',
                'jenkins_master=master-1',
                'total_executors_jenkins=1',
                'total_executors_ec2=2',
                'tag-1-worker_count=1',
            ]
        ])

        actual_data = sorted(get_running_instance_count(
            self.key_name_2, self.key_id, self.secret_key
        ))
        self.assertEqual(actual_data, expected_data)
