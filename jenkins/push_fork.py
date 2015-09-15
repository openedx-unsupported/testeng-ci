"""
This script is intended to be used to push a fork
of the edx platform
"""
import argparse
import logging
import sys

from github import Github

logger = logging.getLogger(__name__)


def main(raw_args):
    # Get args
    desc = "Push a fork of the repo."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        '--user', '-u', dest='username',
        help='GitHub username', required=True)
    parser.add_argument(
        '--pass', '-p', dest='password', required=True,
        help='GitHub password')
    parser.add_argument(
        '--log-level', dest='log_level',
        default="INFO", help="set logging level")
    args = parser.parse_args(raw_args)

    # Set logging level
    logging.getLogger().setLevel(args.log_level.upper())

    github = Github("user", "password")

if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s')
    main(sys.argv[1:])
