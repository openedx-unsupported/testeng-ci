"""
Tests for testeng-ci/aws.
"""
import os
from unittest import TestCase

import boto3
from botocore.exceptions import ClientError
from mock import MagicMock, patch
from testfixtures import LogCapture

from aws.deregister_amis import deregister_amis_by_tag, main


class MockImages:
    """
    Mock boto3 EC2 AMI collection for use in test cases.
    """
    def __init__(self, matching_image_exists, filter_raises_error):
        self.matching_image_exists = matching_image_exists
        self.filter_raises_error = filter_raises_error
        self.image = MagicMock()
        self.image.__str__.return_value = 'test_ami'

    def filter(self, *args, **kwargs):  # pylint: disable=missing-function-docstring
        if self.filter_raises_error:
            raise ClientError(MagicMock(), 'filter')
        if self.matching_image_exists:
            return [self.image]
        return []


class MockEC2:
    """
    Mock boto3 EC2 resource implementation for use in test cases.
    """
    def __init__(self, matching_image_exists=True, filter_raises_error=False):
        self.images = MockImages(matching_image_exists, filter_raises_error)


class DeregisterAmisTestCase(TestCase):
    """
    TestCase class for testing get_running_instances.py.
    """

    def setUp(self):  # pylint: disable=super-method-not-called
        self.args = [
            '--log-level', 'INFO',
        ]

    @patch('boto3.resource', return_value=MockEC2(matching_image_exists=False))
    def test_main(self, mock_ec2):
        """
        Test output of main
        """
        with LogCapture() as capture:
            main(self.args)
            capture.check(
                ('aws.deregister_amis',
                 'INFO',
                 'Finding AMIs tagged with delete_or_keep: delete'),

                ('aws.deregister_amis',
                 'INFO',
                 'No images found matching criteria.')
            )

    @patch('boto3.resource', return_value=MockEC2())
    def test_main_deregister(self, mock_ec2):
        """
        Test that a correctly-tagged AMI is deregistered
        """
        with LogCapture() as capture:
            main(self.args)

            capture.check(
                ('aws.deregister_amis',
                 'INFO',
                 'Finding AMIs tagged with delete_or_keep: delete'),

                ('aws.deregister_amis',
                 'INFO',
                 'Deregistering test_ami')
            )

    @patch('boto3.resource', return_value=MockEC2(matching_image_exists=False))
    def test_main_no_deregister(self, mock_ec2):
        """
        Test that an AMI without proper tags is not de-registered
        """
        with LogCapture() as capture:
            main(self.args)

            capture.check(
                ('aws.deregister_amis',
                 'INFO',
                 'Finding AMIs tagged with delete_or_keep: delete'),

                ('aws.deregister_amis',
                 'INFO',
                 'No images found matching criteria.')
            )

    def test_main_dry_run(self):
        """
        Test that a correctly-tagged AMI is NOT deregistered
        """
        self.args.append('--dry-run')
        mock_ec2 = MockEC2()
        with patch('boto3.resource', return_value=mock_ec2):
            main(self.args)
            mock_ec2.images.image.deregister.assert_not_called()


class DeregisterExceptionTestCase(TestCase):
    """
    Test exceptions that would be thrown from the script.
    """
    @patch('boto3.resource', return_value=MockEC2(filter_raises_error=True))
    def test_cant_get_instances(self, mock_ec2):
        region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        ec2 = boto3.resource('ec2', region_name=region)
        with self.assertRaises(ClientError):
            deregister_amis_by_tag(
                "foo_tag",
                "foo_tag_value",
                dry_run=False,
                ec2=ec2
            )
