"""
handler class to update and verify github status
"""

import datetime
import json
import logging
import os
import time

import jwt
import requests

logging.basicConfig()
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

APP_ID = os.environ.get("EDX_PLATFORM_CHECKS_APP_ID")
REPO_ID = os.environ.get("EDX_PLATFORM_REPO_ID")
INSTALLATION_ID = os.environ.get("EDX_PLATFORM_CHECKS_INSTALLATION_ID")

API_BASE_URL = "https://api.github.com"
PRIVATE_KEY = os.environ.get("EDX_PLATFORM_CHECKS_PRIVATE_KEY")

TOKEN_MACHINE_MAN = 'application/vnd.github.machine-man-preview+json'
TOKEN_ANTIOPE = 'application/vnd.github.antiope-preview+json'


def now(date_type: str = 'ISO') -> str:
    """
    returns current date and time based on specified format
    """
    if date_type == 'ISO':
        return datetime.datetime.now().isoformat() + 'Z'
    if date_type == 'UNIX':
        return time.time()
    raise Exception('Invalid date type')


class GithubTokenHandler:
    """
    class handles creating tokens for checks API access
    """

    def __init__(self):
        self.private_key = PRIVATE_KEY

    def _get_bearer_token(self, duration: int = 60) -> str:
        timestamp = int(now('UNIX'))
        payload = {'iat': timestamp, 'exp': timestamp + duration, 'iss': APP_ID}
        return jwt.encode(payload, self.private_key, algorithm='RS256')

    def get_access_token(self) -> str:
        """
        returns access token for creating checks
        """
        headers = {"Accept": TOKEN_MACHINE_MAN, "Authorization": f"Bearer {self._get_bearer_token()}"}
        data = {"repository_ids": [REPO_ID], "permissions": {"checks": "write"}}
        response = requests.post(
            f"{API_BASE_URL}/app/installations/{INSTALLATION_ID}/access_tokens",
            headers=headers, json=data)

        result = response.json()
        if response.status_code != 201:
            raise Exception('Unexpected status code {}'.format(response.status_code), result.get('message'))
        return result['token']


class GithubChecksHandler:
    """
    class handles creating and verifying checks
    """
    def __init__(self):
        self._set_env_variables()
        self._set_github_api_token()

    def _set_github_api_token(self):
        self.token = GithubTokenHandler().get_access_token()

    def _set_env_variables(self):
        """
        reads env variables and sets local variables
        """
        self.conclusion = os.environ.get("BUILD_STATUS")
        self.target_url = os.environ.get("TARGET_URL")
        self.description = os.environ.get("DESCRIPTION")
        self.check_name = os.environ.get("CONTEXT")
        self.organization = os.environ.get("GITHUB_ORG")
        self.repo = os.environ.get("GITHUB_REPO")
        self.commit_id = os.environ.get("GIT_SHA")

    def _get_default_headers(self):
        """
        returns default request headers
        """
        return {
            'Content-type': 'application/json',
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def _get_payload(self):
        """
        returns payload for creating checks
        """

        payload = {
            "head_sha": self.commit_id,
            "conclusion": self.conclusion,
            "details_url": self.target_url,
            "output": {"description": self.description},
            "name": self.check_name + "_check"
        }

        build_status = 'in_progress'
        if self.conclusion in ['success', 'failure']:
            build_status = 'completed'
            payload.update({"completed_at": now()})
        elif self.conclusion in ['neutral']:
            payload.update({"started_at": now()})

        payload.update({"status": build_status})
        return payload

    def _create_new_check(self):
        """
        creates a new github check for given commit
        """

        url = f"{API_BASE_URL}/repos/{self.organization}/{self.repo}/check-runs/"
        LOGGER.info("URL: {0}".format(url))
        response = requests.post(url,
                                 data=json.dumps(self._get_payload()),
                                 headers=self._get_default_headers())

        LOGGER.info("Create check run response: {0}".format(response.content))

    def _verify_check_status(self):
        """
        makes sure the created check exists
        """
        response = requests.get(
            f"{API_BASE_URL}/repos/{self.organization}/{self.repo}/commits/{self.commit_id}/check-runs",
            headers=self._get_default_headers()
        )
        LOGGER.info("Get check runs response:")
        LOGGER.info(response.content)

        response_object = json.loads(response.content)
        check_name_status = next(
            filter(lambda check_run: check_run.get('name') == self.check_name, response_object.get('check_runs')), None
        )

        assert check_name_status.get('state') == self.conclusion

    def handle(self):
        self._create_new_check()
        self._verify_check_status()


def main():
    GithubChecksHandler().handle()


if __name__ == "__main__":
    main()
