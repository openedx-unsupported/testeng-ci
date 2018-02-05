import argparse
import boto
from boto.exception import EC2ResponseError
from datetime import datetime, timedelta
import logging
import os
import sys

logger = logging.getLogger(__name__)


def get_ec2_connection(aws_access_key_id, aws_secret_access_key):
    return boto.connect_ec2(aws_access_key_id, aws_secret_access_key)


def terminate_instances(tag_key, tag_value, dry_run, connection):
    """
    Terminate instances that are found according to tag key/value pairs.
    """
    tag_key_string = "tag:{tag_key}".format(tag_key=tag_key)

    logger.info("Finding instances tagged with {key}: {value}".format(
        key=tag_key,
        value=tag_value,
    ))
    running_instances = []
    try:
        reservations = connection.get_all_instances(filters={tag_key_string: tag_value})
        for r in reservations:
            for i in r.instances:
                if i.state == 'running':
                    fmt =  '%Y-%m-%dT%H:%M:%S.000Z'
                    launch_time = datetime.strptime(i.launch_time, fmt)
                    elapsed =  datetime.now() - launch_time
                    if elapsed > timedelta(hours=2):
                        running_instances.append(i)

    except EC2ResponseError:
        logger.error("An error occurred gathering images.")
        logger.error(EC2ResponseError.message)
        raise

    if len(running_instances) == 0:
        logger.info('No running instances found matching criteria.')
        return

    for i in running_instances:
        logger.info("Terminating {instance}".format(instance=str(i)))
        if dry_run:
            logger.info("--> Dry run: skipping termination")
        else:
            i.terminate()


def main(raw_args):
    desc = (
        "Terminate 'Packer Builder' EC2 instances that are still running >2hrs"
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
        Do not terminate any instances, just list the currently running
        ones that are found matching the Name "Packer Builder".
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
    terminate_instances("Name", "Packer Builder", args.dry_run, conn)

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s')
    main(sys.argv[1:])
