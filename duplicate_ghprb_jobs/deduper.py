"""
This script is intended to be used to abort outdated builds
on a jenkins job that uses the ghprbPlugin. In this case,
an outdated build is one for which the PR that triggered it
has a more recently triggered build also running.
"""
from collections import defaultdict
from operator import itemgetter
import argparse
import json
import logging
import re
import requests
import sys

logging.basicConfig(format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def append_url(base, addition):
    """
    Add something to a url, ensuring that there are the
    right amount of `/`.

    :Args:
        base: The original url.
        addition: the thing to add to the end of the url

    :Returns: The combined url as a string of the form
        `base/addition`
    """
    if not base.endswith('/'):
        base += '/'
    if addition.startswith('/'):
        addition = addition[1:]
    return base + addition


class GhprbOutdatedBuildAborter:
    """
    A class for programatically finding and aborting outdated
    jenkins builds that were started using the GHPRB plugin.

    :Args:
        job_url: URL of jenkins job that uses the GHPRB plugin
        username: jenkins userme
        token: jeknins api token
    """
    def __init__(self, job_url, username, token):
        self.job_url = job_url
        self.auth = (username, token)

    @staticmethod
    def _aborted_description(current_build_id, pr):
        """
        :Args:
            current_build_id: the id of the most recently started
                build for the PR
            pr: the PR id

        :Returns: A description (string)
        """
        return ("[PR #{}] Build automatically aborted because"
                " there is a newer build for the same PR. See build"
                " #{}.".format(pr, current_build_id))

    def abort_duplicate_builds(self):
        """
        Find running builds of the ghprb job at self.job_url.
        If there are multiple jobs running for the same PR,
        abort all but the newest build. It updates the build
        description of aborted jobs to indicate why they where
        stopped.
        """
        data = self.get_json()
        builds = self.get_running_builds(data)
        self.stop_duplicates(builds)

    def get_json(self):
        """
        Get build data for a given job_url.

        :Returns:
            A python dict from the jeknins api response including:
            * builds: a list of dicts, each containing:
                ** building: Boolean of whether it is actively building
                ** timestamp: the time the build started
                ** number: the build id number
                ** actions: a list of 'actions', from which the only
                    item used in this script is 'parameters' which can
                    be used to find the PR number.
        """
        api_url = append_url(self.job_url, '/api/json')

        response = requests.get(
            api_url,
            params={
                "tree": ("builds[building,timestamp,"
                         "number,actions[parameters[*]]]"),
            }
        )

        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_running_builds(data):
        """
        Return build data for currently running builds.

        :Args:
            data: the return value of self.get_json()

        :Returns:
            build_data: a dict where keys are a PR id and the value is
                a list of 'builds' for the PR. Each item in the list
                has the data for the build as returned in self.get_json.
        """
        build_data = defaultdict(list)

        # This is used to find the PR id instead of having a bunch of
        # messy loops.
        pr_id_regex = (r"{[\s-]*\"name\"[\s-]*:[\s-]*\"ghprbPullId\""
                       r"[\s-]*,[\s-]*\"value\"[\s-]*:[\s-]*\"[\d]*\"}")

        for b in data['builds']:
            if b['building']:
                pr_id_data_str = re.search(
                    pr_id_regex, json.dumps(b['actions'])).group(0)
                pr_id_data = json.loads(pr_id_data_str)
                pr_id = pr_id_data['value']
                build_data[pr_id].append(b)

        return build_data

    def stop_duplicates(self, build_data):
        """
        Finds PRs that have multiple builds actively running.

        :Args:
            build_data: the data returned by self.get_running_builds()
        """
        lines = []
        for pr, builds in build_data.iteritems():
            if len(builds) > 1:
                # Sort builds by timestamp (newest to oldest)
                sorted_builds = sorted(
                    builds, key=itemgetter('timestamp'), reverse=True)

                # Most recently started build is the first in the list
                current_build_id = sorted_builds[0]['number']

                # Any other builds are assumed to be outdated
                old_build_ids = [b['number'] for b in sorted_builds[1:]]

                lines.append("PR #{}:".format(pr))
                lines.append("\tNum running builds: {}".format(
                    len(sorted_builds)))
                lines.append("\tCurrent build: {}".format(
                    current_build_id))
                lines.append("\tOutdated builds: {}".format(
                    old_build_ids))

                desc = self._aborted_description(current_build_id, pr)

                for b in old_build_ids:
                    try:
                        self.stop_build(b)
                        self.update_build_desc(b, desc)
                    except Exception as e:
                        logger.error(e.message)

        if lines:
            out = ("\n---------------------------------"
                   "\n** Extra running builds found. **"
                   "\n---------------------------------\n")
            out += "\n".join(lines)
            logger.info(out)
        else:
            logger.info("No extra running builds found.")

    def update_build_desc(self, build_id, description):
        """
        Updates build description.

        :Args:
            build_id: id number of build to update
            description: the new description
        """
        build_url = append_url(self.job_url, str(build_id))
        url = append_url(build_url, "/submitDescription")

        response = requests.post(
            url,
            auth=self.auth,
            params={
                'description': description,
            },
        )

        logger.info("Updating description for build #{}. Response: {}".format(
            build_id, response.status_code))

        response.raise_for_status()
        return response.ok

    def stop_build(self, build_id):
        """
        Stops a build.

        :Args:
            build_id: id number of build to abort
        """
        build_url = append_url(self.job_url, str(build_id))
        url = append_url(build_url, "/stop")

        response = requests.post(url, auth=self.auth)

        logger.info("Aborting build #{}. Response: {}".format(
            build_id, response.status_code))

        response.raise_for_status()
        return response.ok


def deduper_main(raw_args):
    # Get args
    parser = argparse.ArgumentParser(
        description="Programatically abort oldest builds for"
                    "a PR so that only one is running.")
    parser.add_argument('--token', '-t', dest='token',
                        help='jeknins api token', required=True)
    parser.add_argument('--user', '-u', dest='username',
                        help='jenkins username', required=True)
    parser.add_argument('--job', '-j', dest='job_url',
                        help='URL of jenkins job that uses the GHPRB plugin',
                        required=True)
    parser.add_argument('--log-level', dest='log_level',
                        default="INFO", help="set logging level")
    args = parser.parse_args(raw_args)

    # Set logging level
    logger.setLevel(args.log_level.upper())

    # Abort extra jobs
    deduper = GhprbOutdatedBuildAborter(
        args.job_url, args.username, args.token)
    deduper.abort_duplicate_builds()


if __name__ == '__main__':
    deduper_main(sys.argv[1:])
