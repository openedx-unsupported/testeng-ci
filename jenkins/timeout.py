"""
This script is intended to be used to abort builds that are assumed to be
stuck because they have exceeded the expected max time.
"""
import argparse
import datetime
import logging
import sys

from .job import JenkinsJob

logger = logging.getLogger(__name__)


class BuildTimeout:

    """
    A class for programatically finding and aborting stuck builds.

    :Args:
        job: An instance of jenkins_api.job.JenkinsJob
    """

    def __init__(self, job, timeout):
        self.job = job
        self.timeout = int(timeout)

    @staticmethod
    def _aborted_description(timeout, build):
        """
        :Args:
            timeout: the timeout length in minutes
            pr: the PR id

        :Returns: A description (string)
        """
        return ("Build #{} automatically aborted because it has exceeded"
                " the timeout of {} minutes.".format(build, timeout))

    def abort_stuck_builds(self):
        """
        Find running builds of the job at self.job_url.
        If there are builds that have been running for longer than
        the set timeout, abort them. It updates the build
        description of aborted builds to indicate why they where
        stopped.
        """
        data = self.job.get_json()
        builds = self.get_stuck_builds(data)
        self.stop_stuck_builds(builds)

    def get_stuck_builds(self, data):
        """
        Return build data for currently running builds.

        :Args:
            data: the return value of self.get_json()

        :Returns:
            build_data: a list of build numbers as strings
        """
        long_running_builds = []
        now = datetime.datetime.utcnow()

        for build in data['builds']:
            # Need to divide by 1000 to get time in seconds
            start_time = datetime.datetime.utcfromtimestamp(
                build['timestamp'] / 1000.0)
            time_delta = now - start_time
            min_since_start = time_delta.total_seconds() / 60.0

            if build['building'] and min_since_start >= self.timeout:
                long_running_builds.append(build['number'])

        return long_running_builds

    def stop_stuck_builds(self, build_nums):
        """
        Finds PRs that are stuck and abort them.

        :Args:
            build_data: the data returned by self.get_running_builds()
        """

        lines = []
        for b in build_nums:
            lines.append(f"Build #{b} aborted due to timeout.")
            desc = self._aborted_description(self.timeout, b)

            try:
                self.job.stop_build(b)
                self.job.update_build_desc(b, desc)
            except Exception as e:  # pylint: disable=broad-except
                logger.error(e)

        if lines:
            out = ("\n---------------------------------"
                   "\n** Stuck builds found. **"
                   "\n---------------------------------\n")
            out += "\n".join(lines)
            logger.info(out)
        else:
            logger.info("No stuck builds found.")


def timeout_main(raw_args):  # pylint: disable=missing-function-docstring
    # Get args
    parser = argparse.ArgumentParser(
        description="Programatically abort builds that have been running"
                    "longer than a specified time")
    parser.add_argument('--token', '-t', dest='token',
                        help='jeknins api token', required=True)
    parser.add_argument('--user', '-u', dest='username',
                        help='jenkins username', required=True)
    parser.add_argument('--job', '-j', dest='job_url',
                        help='URL of jenkins job that uses the GHPRB plugin',
                        required=True)
    parser.add_argument('--timeout', dest='timeout',
                        help='A time in minutes at which we should consider'
                        'a build to be stuck',
                        required=True)
    parser.add_argument('--log-level', dest='log_level',
                        default="INFO", help="set logging level")
    args = parser.parse_args(raw_args)

    # Set logging level
    logging.getLogger().setLevel(args.log_level.upper())

    # Abort builds that exceed timeout
    job = JenkinsJob(args.job_url, args.username, args.token)
    timer = BuildTimeout(job, args.timeout)
    timer.abort_stuck_builds()


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s')
    timeout_main(sys.argv[1:])
