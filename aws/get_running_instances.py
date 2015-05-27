"""
Use boto to get the number of running or pending EC2 instances matching a key
name.

Usage:
    If you've defined the AWS credentials as environment variables or in a
    .boto file, then use:
        `python get_running_instances.py -k some-key-name`

    Else, you can add the aws keys as arguments to the above command:
        ** '--aws-access-key-id' or '-i'
        ** '--aws-secret-access-key' or '-s'
"""
import argparse
import boto
import logging
import os
import sys


logging.basicConfig(format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def get_running_instances(key_name, aws_access_key_id, aws_secret_access_key):
    """
    Logs and returns (as a string) the number of EC2 instances matching
    `key_name` that are running or pending.

    :Args:
        key_name: the ec2 key_name to match.
        aws_access_key_id
        aws_secret_access_key
    """
    ec2conn = boto.connect_ec2(aws_access_key_id, aws_secret_access_key)
    reservations = ec2conn.get_all_instances()
    instances = [
        i for r in reservations for i in r.instances
        if i.state in ('running', 'pending') and i.key_name == key_name
    ]

    num_running = len(instances)
    logger.info(
        "Number of {} instances on EC2: {}".format(key_name, str(num_running))
    )
    return num_running


def main(raw_args):
    desc = (
        "Use boto to get the number of running or pending EC2 instances "
        "matching the given key name."
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
        '--key-name', '-k',
        dest='key_name',
        help='aws ec2 key name',
    )
    parser.add_argument(
        '--log-level',
        dest='log_level',
        help="set logging level",
        default="INFO",
    )
    args = parser.parse_args(raw_args)

    # Set logging level
    logging.getLogger().setLevel(args.log_level.upper())
    get_running_instances(
        args.key_name, args.aws_access_key_id, args.aws_secret_access_key
    )


if __name__ == "__main__":
    main(sys.argv[1:])
