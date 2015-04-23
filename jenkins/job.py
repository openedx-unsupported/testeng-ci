"""
A class to interact with a jenkins job API
"""
import logging
import requests

from helpers import append_url


logging.basicConfig(format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger('requests').setLevel('ERROR')


class JenkinsJob:

    """
    A class for interacting with the jenkins job API

    :Args:
        job_url: URL of jenkins job
        username: jenkins username
        token: jenkins api token
    """

    def __init__(self, job_url, username, token):
        self.job_url = job_url
        self.auth = (username, token)

    def get_json(self):
        """
        Get build data for a given job_url.

        :Returns:
            A python dict from the jenkins api response including:
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
