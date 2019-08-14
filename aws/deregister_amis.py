"""
Use boto to deregister AMIs that match a given tag key-value pair.

That tag key-value pair is hardcoded to:
    delete_or_keep: delete

Usage:
    If you've defined the AWS credentials as environment variables or in a
    .boto file, then use:
        `python deregister_amis.py

    Else, you can add the aws keys as arguments to the above command:
        ** '--aws-access-key-id' or '-i'
        ** '--aws-secret-access-key' or '-s'

    If you don't want to deregister AMIs, but you'd like to know which ones
    you'd deregister if you ran the command, then use the --dry-run switch.

"""
from __future__ import absolute_import

import argparse
import boto
from boto.exception import EC2ResponseError
import logging
import os
import sys

logger = logging.getLogger(__name__)


def get_ec2_connection(aws_access_key_id, aws_secret_access_key):
    return boto.connect_ec2(aws_access_key_id, aws_secret_access_key)


def deregister_amis_by_tag(tag_key, tag_value, dry_run, connection):
    """
    Deregisters AMIs that are found according to tag key/value pairs.
    """

    tag_key_string = "tag:{tag_key}".format(tag_key=tag_key)

    logger.info("Finding AMIs tagged with {key}: {value}".format(
        key=tag_key,
        value=tag_value,
    ))
    try:
        amis = connection.get_all_images(filters={tag_key_string: tag_value})
    except EC2ResponseError:
        logger.error("An error occurred gathering images.")
        logger.error(EC2ResponseError.message)
        raise

    if len(amis) == 0:
        logger.info('No images found matching criteria.')
        return
    for i in amis:
        logger.info("Deregistering {image}".format(image=str(i)))
        if dry_run:
            logger.info("--> Dry run: skipping deregister")
        else:
            i.deregister()


def main(raw_args):
    desc = (
        "Deregister EC2 images that are tagged for 'delete_or_keep' with "
        "'delete' as the tag value."
    )
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        '--aws-access-key-id', '-i',
        dest='aws_access_key_id',
        help='aws access key id',
        default=os.environ.get("AWS_ACCESS_KEY_ID"),
        )
    parser.add_argument(
        '--aws-secret-access-key', '-s',
        dest='aws_secret_access_key',
        help='aws secret access key',
        default=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        help="""
        Do not deregister any AMIs, just list the ones
        that are found matching the tag key/value pair.
        """
    )
    parser.add_argument(
        '--log-level',
        dest='log_level',
        help="set logging level",
        choices=[
            'DEBUG', 'debug',
            'INFO', 'info',
            'WARNING', 'warning',
            'ERROR', 'error',
            'CRITICAL', 'critical',
        ],
        default="INFO",
    )
    args = parser.parse_args(raw_args)

    # Set logging level
    logging.getLogger(__name__).setLevel(args.log_level.upper())
    conn = get_ec2_connection(
        args.aws_access_key_id,
        args.aws_secret_access_key
    )
    deregister_amis_by_tag("delete_or_keep", "delete", args.dry_run, conn)

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s')
    main(sys.argv[1:])
