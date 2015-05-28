"""
Use the jenkins queue and computer APIs to capture info about workers.

Usage:
    `python jenkins/workers.py -j https://example.jenkins.com`

Example Output:
    [INFO] Counts of workers and queue length from Jenkins API:
    [INFO] Build Queue Length: 0
    [INFO] Busy Executors: 25
    [INFO] Total Executors: 37
"""
import argparse
import logging
import requests
import sys
from helpers import append_url


logging.basicConfig(format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger('requests').setLevel('ERROR')


def log_queue_length(jenkins_url):
    """
    Logs the current queue length for the given jenkins instance.

    Args:
        jenkins_url: the url of a jenkins instance
    """
    api_url = append_url(jenkins_url, '/queue/api/json')
    response = requests.get(api_url)
    response.raise_for_status()
    data = response.json()
    length = len(data['items'])
    logger.info('Build Queue Length: {}'.format(length))


def log_worker_counts(jenkins_url):
    """
    Logs the current count of workers for the given jenkins instance.
    Logs counts of both busy executors and total executors.

    Args:
        jenkins_url: the url of a jenkins instance
    """
    api_url = append_url(jenkins_url, '/computer/api/json')
    response = requests.get(
        api_url,
        params={'tree': "busyExecutors,totalExecutors"}
    )
    response.raise_for_status()
    data = response.json()

    logger.info('Busy Executors: {}'.format(data['busyExecutors']))
    logger.info('Total Executors: {}'.format(data['totalExecutors']))


def main(raw_args):
    """
    Parses args and calls log_queue_length and log_worker_counts.
    """
    # Get args
    parser = argparse.ArgumentParser(
        description="Log the current length of the build queue."
    )
    parser.add_argument(
        '--jenkins-url', '-j',
        dest='jenkins_url',
        help='URL of jenkins instance',
        required=True
    )
    parser.add_argument(
        '--log-level',
        dest='log_level',
        default="INFO",
        choices=[
            'DEBUG', 'debug',
            'INFO', 'info',
            'WARNING', 'warning',
            'ERROR', 'error',
            'CRITICAL', 'critical',
        ],
        help="set logging level"
    )
    args = parser.parse_args(raw_args)

    # Set logging level
    logging.getLogger().setLevel(args.log_level.upper())

    # Log the current queue length and worker counts
    logger.info(
        "Counts of workers and queue length for {}".format(args.jenkins_url)
    )
    log_queue_length(args.jenkins_url)
    log_worker_counts(args.jenkins_url)


if __name__ == '__main__':
    main(sys.argv[1:])
