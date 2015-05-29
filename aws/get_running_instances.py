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

Example Output:
    2015-05-28 16:59:02,421 [INFO] datasrc=aws, \
    jenkins_master=example.jenkins.com, total_executors_jenkins=86, \
    total_executors_ec2=86, desc-1-worker_count=5, desc-2-worker_count=81

Assumptions:
    This is implemented with some assumptions about the way that workers are
    tagged. In particuar, it is assumed that the tags `master` and `worker` are
    used. Values for `master` are expected to be the netloc of the jenkins
    master.  Values for `worker` are expected to match the description given
    in the Jenkins EC2 plugin configuration, but without ending in '-worker'.
    For example, if my worker description in jenkins is 'abc-worker', then
    the worker tag in EC2 is expected to be 'abc'.
"""
import argparse
import boto
import logging
import os
import sys
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)


def sort_by_master_and_worker(reservations, key_name):
    """
    Sorts the list of boto `Reservation` objects into a dictionary,
    mapping `master` tags to a counter of `worker` tags for that master.
    Only running and pending instances matching the given `key_name` will be
    included. Instances without `master` or `worker` tags will be sorted as
    'untagged'.

    :Args:
        reservations: a list of boto `Reservation` objects
        key_name: an ec2 key_name to match

    :Returns: A tuple(data, total_instances) where data is the restructured
        data and total_instances is the total number of running or pending
        instances matching key_name.
    """
    data = defaultdict(Counter)
    total_instances = 0
    for r in reservations:
        for i in r.instances:
            if i.state in ('running', 'pending') and i.key_name == key_name:
                total_instances += 1
                master = i.tags.get('master', 'untagged')
                worker = i.tags.get('worker', 'untagged')
                data[master].update([worker])
    return data, total_instances


def get_running_instance_count(
    key_name, aws_access_key_id, aws_secret_access_key
):
    """
    Logs and returns (as a string) the number of EC2 instances matching
    `key_name` that are running or pending.

    :Args:
        key_name: the ec2 key_name to match.
        aws_access_key_id
        aws_secret_access_key

    :Raises:
        EC2ResponseError
    """
    ec2conn = boto.connect_ec2(aws_access_key_id, aws_secret_access_key)
    reservations = ec2conn.get_all_instances()

    sorted_data, total_instances = sort_by_master_and_worker(
        reservations, key_name)

    output = []
    for master, workers in sorted_data.iteritems():
        workers_on_master = sum(workers.values())
        fields = [
            'datasrc=aws',
            'jenkins_master={}'.format(master),
            'total_executors_jenkins={}'.format(str(workers_on_master)),
            'total_executors_ec2={}'.format(str(total_instances)),
        ]

        fields.extend([
            '{}-worker_count={}'.format(worker, count)
            for worker, count in workers.iteritems()
        ])

        output.append(fields)

    return output


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
    data = get_running_instance_count(
        args.key_name, args.aws_access_key_id, args.aws_secret_access_key
    )

    for data_group in data:
        logger.info(', '.join(data_group))


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s')
    main(sys.argv[1:])
