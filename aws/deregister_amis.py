"""
Use boto3 to deregister AMIs that match a given tag key-value pair.
This is used by the clean-up-AMIs Jenkins job.

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
import argparse
import logging
import os
import sys

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def deregister_amis_by_tag(tag_key, tag_value, dry_run, ec2):
    """
    Deregisters AMIs that are found according to tag key/value pairs.
    """

    tag_key_string = f"tag:{tag_key}"

    logger.info("Finding AMIs tagged with {key}: {value}".format(
        key=tag_key,
        value=tag_value,
    ))
    try:
        filters = [{'Name': tag_key_string, 'Values': [tag_value]}]
        amis = ec2.images.filter(Filters=filters)
    except ClientError:
        logger.exception("An error occurred gathering images.")
        raise

    if len(list(amis)) == 0:
        logger.info('No images found matching criteria.')
        return
    for i in amis:
        logger.info("Deregistering {image}".format(image=str(i)))
        if dry_run:
            logger.info("--> Dry run: skipping deregister")
        else:
            i.deregister()


def main(raw_args):  # pylint: disable=missing-function-docstring
    desc = (
        "Deregister EC2 images that are tagged for 'delete_or_keep' with "
        "'delete' as the tag value."
    )
    parser = argparse.ArgumentParser(description=desc)
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
    logging.getLogger('boto3').setLevel(logging.INFO)
    logging.getLogger('botocore').setLevel(logging.INFO)
    region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
    ec2 = boto3.resource('ec2', region_name=region)
    deregister_amis_by_tag("delete_or_keep", "delete", args.dry_run, ec2)


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s')
    main(sys.argv[1:])
