"""
This script is intended to be used to abort outdated builds
on a jenkins job that uses the ghprbPlugin. In this case,
an outdated build is one for which the PR that triggered it
has a more recently triggered build also running.
"""
from collections import defaultdict
from operator import itemgetter
import argparse
import logging
import sys

from jenkins.job import JenkinsJob
from jenkins.build import Build


LOGGER = logging.getLogger(__name__)


class GhprbOutdatedBuildAborter(object):

    """
    A class for programmatically finding and aborting outdated
    jenkins builds that were started using the GHPRB plugin.

    :Args:
        job: An instance of jenkins_api.job.JenkinsJob
    """

    def __init__(self, job, one_per_author=False):
        self.job = job
        self.one_per_author = one_per_author

    @staticmethod
    def _aborted_description(current_build_id, pull_request):
        """
        :Args:
            current_build_id: the id of the most recently started
                build for the PR
            pr: the PR id

        :Returns: A description (string)
        """
        return ("[PR #{}] Build automatically aborted because"
                " there is a newer build for the same PR. See build"
                " #{}.".format(pull_request, current_build_id))

    def abort_duplicate_builds(self):
        """
        Find running builds of the ghprb job at self.job_url.
        If there are multiple jobs running for the same PR,
        abort all but the newest build. It updates the build
        description of aborted jobs to indicate why they where
        stopped.
        """
        data = self.job.get_json()
        builds = self.get_running_builds(data)
        self.stop_duplicates(builds)

    @staticmethod
    def get_running_builds(data):
        """
        Return build data for currently running builds.

        :Args:
            data (dict): the return value of self.get_json()

        :Raises:
            KeyError if there is no 'builds' key in the data

        :Returns:
            dict: where keys are a PR id and the value is
            a list of 'builds' for the PR. Each item in the list
            has the data for the build as returned in self.get_json.
        """
        build_data = defaultdict(list)

        for bld in data['builds']:
            build = Build(bld)
            if build.isbuilding:
                build_data[build.pr_id].append(bld)

        return build_data

    def stop_all_but_most_recent(self, pull_request, builds):
        """
        Stop all the builds in the list but the most recently initiated.

        :Args:
            pr (str): PR number of the build, used for logging purposes
            builds (list of dict): list of running builds for that PR

        :Returns:
            list of str: output to add for logging
        """
        output = []
        if len(builds) > 1:
            # Sort builds by timestamp (newest to oldest)
            sorted_builds = sorted(
                builds, key=itemgetter('timestamp'), reverse=True)

            # Most recently started build is the first in the list
            current_build_id = sorted_builds[0]['number']

            # Any other builds are assumed to be outdated
            old_build_ids = [bld['number'] for bld in sorted_builds[1:]]

            output.append("PR #{}:".format(pull_request))
            output.append("\tNum running builds: {}".format(
                len(sorted_builds)))
            output.append("\tCurrent build: {}".format(
                current_build_id))
            output.append("\tOutdated builds: {}".format(
                old_build_ids))

            desc = self._aborted_description(current_build_id, pull_request)

            for bld in old_build_ids:
                try:
                    self.job.stop_build(bld)
                    self.job.update_build_desc(bld, desc)
                except Exception as err:  # pylint: disable=broad-except
                    LOGGER.error(err.message)
        return output

    def stop_duplicates(self, build_data):
        """
        Finds PRs that have multiple builds actively running.

        :Args:
            build_data: the data returned by self.get_running_builds()
        """
        lines = []
        for pull_request, builds in build_data.iteritems():
            if self.one_per_author:
                # Assemble a dict where the key is the author and the
                # value is a list of that author's builds.
                pr_builds = defaultdict(list)
                for build in builds:
                    author = Build(build).author
                    pr_builds[author].append(build)

                # Now for each author, stop all but the most
                # recent build.
                for build_list in pr_builds.itervalues():
                    output = self.stop_all_but_most_recent(
                        pull_request,
                        build_list
                    )
                    if len(output) > 0:
                        lines.extend(output)

            else:
                output = self.stop_all_but_most_recent(pull_request, builds)
                if len(output) > 0:
                    lines.extend(output)

        if len(lines) > 0:
            out = ("\n---------------------------------"
                   "\n** Extra running builds found. **"
                   "\n---------------------------------\n")
            out += "\n".join(lines)
            LOGGER.info(out)
        else:
            LOGGER.info("No extra running builds found.")


def deduper_main(raw_args):
    """
    Main for the deduper script
    """
    # Get args
    desc = "Programatically abort older, still-running builds for a PR."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        '--token', '-t', dest='token',
        help='jenkins api token', required=True)
    parser.add_argument(
        '--user', '-u', dest='username',
        help='jenkins username', required=True)
    parser.add_argument(
        '--job', '-j', dest='job_url', required=True,
        help='URL of jenkins job that uses the GHPRB plugin')
    parser.add_argument(
        '--one-per-author', dest='one_per_author', action='store_true',
        help="Leave one build for each unique last commit author for a PR.")
    parser.add_argument(
        '--log-level', dest='log_level',
        default="INFO", help="set logging level")
    args = parser.parse_args(raw_args)

    # Set logging level
    logging.getLogger().setLevel(args.log_level.upper())

    # Abort extra jobs
    job = JenkinsJob(args.job_url, args.username, args.token)
    deduper = GhprbOutdatedBuildAborter(job, args.one_per_author)
    deduper.abort_duplicate_builds()


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s')
    deduper_main(sys.argv[1:])
