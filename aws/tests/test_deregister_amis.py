"""
Tests for testeng-ci/aws.
"""
from __future__ import absolute_import

import boto
from boto.exception import EC2ResponseError
from aws.deregister_amis import(
    main, get_ec2_connection, deregister_amis_by_tag)
from moto import mock_ec2
from testfixtures import LogCapture
from unittest import TestCase


@mock_ec2
class DeregisterAmisTestCase(TestCase):
    """
    TestCase class for testing get_running_instances.py.
    """

    def setUp(self):
        self.key_id = 'my-key-id'
        self.secret_key = 'my-secret-key'
        self.conn = boto.connect_ec2(self.key_id, self.secret_key)
        self.args = [
            '-i', self.key_id,
            '-s', self.secret_key,
            '--log-level', 'INFO',
        ]

    def _get_test_image(self):
        test_image_id = 'ami-11122278'
        reservation = self.conn.run_instances(test_image_id)
        self.conn.create_image(
            name='test-ami',
            instance_id=reservation.instances[0].id
        )
        return self.conn.get_all_images()[0]

    def test_main(self):
        """
        Test output of main
        """
        with LogCapture() as l:
            main(self.args)
            l.check(
                ('aws.deregister_amis',
                 'INFO',
                 'Finding AMIs tagged with delete_or_keep: delete'),

                ('aws.deregister_amis',
                 'INFO',
                 'No images found matching criteria.')
            )

    def test_main_deregister(self):
        """
        Test that a correctly-tagged AMI is deregistered
        """

        test_ami = self._get_test_image()
        test_ami.add_tag('delete_or_keep', 'delete')
        with LogCapture() as l:
            main(self.args)

            l.check(
                ('aws.deregister_amis',
                 'INFO',
                 'Finding AMIs tagged with delete_or_keep: delete'),

                ('aws.deregister_amis',
                 'INFO',
                 'Deregistering {image_id}'.format(image_id=test_ami))
            )
        self.assertEqual(len(self.conn.get_all_images()), 0)

    def test_main_no_deregister(self):
        """
        Test that an AMI without proper tags is not de-registered
        """
        test_ami = self._get_test_image()
        # Flag AMI as 'keep'
        test_ami.add_tag('delete_or_keep', 'keep')

        with LogCapture() as l:
            main(self.args)

            l.check(
                ('aws.deregister_amis',
                 'INFO',
                 'Finding AMIs tagged with delete_or_keep: delete'),

                ('aws.deregister_amis',
                 'INFO',
                 'No images found matching criteria.')
            )
        self.assertEqual(len(self.conn.get_all_images()), 1)

    def test_main_dry_run(self):
        """
        Test that a correctly-tagged AMI is NOT deregistered
        """
        test_ami = self._get_test_image()
        test_ami.add_tag('delete_or_keep', 'delete')

        self.args.append('--dry-run')
        main(self.args)
        self.assertEqual(len(self.conn.get_all_images()), 1)


class DergisterExceptionTestCase(TestCase):
    """
    Test exceptions that would be thrown from the script. Note that boto is
    not mocked in this class. It will make actual network calls.

    """

    def setUp(self):
        self.key_id = 'FAKEBADKEY'
        self.secret_key = 'FAKEBADSECRET'

    def test_cant_get_instances(self):
        conn = get_ec2_connection(self.key_id, self.secret_key)
        with self.assertRaises(EC2ResponseError):
            deregister_amis_by_tag(
                "foo_tag",
                "foo_tag_value",
                dry_run=False,
                connection=conn
            )
