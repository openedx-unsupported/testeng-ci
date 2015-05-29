"""
Use the jenkins queue and computer APIs to capture info about workers.

Usage:
    `python jenkins/workers.py -j https://example.jenkins.com`

Example Output:
    2015-05-28 15:03:48,007 [INFO] datasrc=jenkins, \
    jenkins_master=example.jenkins.com, queue_length=2, \
    busy_executors_jenkins=36, total_executors_jenkins=40, \
    worker-desc-1_count=34, worker-desc-2_count=5, master_count=1

Because these are logged with a timestamp and formatted for automatic field
extraction, splunk should recognize this as an event and make it easy to
inspect the data there.
(See http://dev.splunk.com/view/logging-best-practices/SP-CAAADP6)

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
import logging
import requests
import sys
import urlparse
from collections import Counter
from helpers import append_url


logger = logging.getLogger(__name__)
logging.getLogger('requests').setLevel('ERROR')


def get_queue_data(jenkins_url):
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
    fields = ['queue_length={}'.format(length)]
    return fields


def get_computer_data(jenkins_url):
    """
    Logs the current count of workers for the given jenkins instance.
    Logs counts of both busy executors and total executors.

    Args:
        jenkins_url: the url of a jenkins instance
    """
    api_url = append_url(jenkins_url, '/computer/api/json')
    response = requests.get(
        api_url,
        params={
            'tree': (
                "busyExecutors,totalExecutors,computer[displayName,offline]"
            )
        }
    )
    response.raise_for_status()
    data = response.json()

    fields = [
        'busy_executors_jenkins={}'.format(data['busyExecutors']),
        'total_executors_jenkins={}'.format(data['totalExecutors']),
    ]

    # displayName is made up of two parts -- the description as set in jenkins
    # ami config and the the instance id. We just want just the description
    # of workers that are online.
    worker_counts = Counter([
        c['displayName'].split("(i-")[0] for c in data['computer']
        if not c['offline']
    ])

    fields.extend([
        '{}_count={}'.format(type.strip(), count)
        for type, count in worker_counts.iteritems()
    ])

    return fields


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
    logging.getLogger(__name__).setLevel(args.log_level.upper())

    # Log the current queue length, worker counts, and jenkins_url
    master = urlparse.urlsplit(args.jenkins_url).netloc
    data_fields = [
        'datasrc=jenkins',
        'jenkins_master={}'.format(master),
    ]
    data_fields.extend(get_queue_data(args.jenkins_url))
    data_fields.extend(get_computer_data(args.jenkins_url))
    logger.info(', '.join(data_fields))


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s')
    main(sys.argv[1:])
