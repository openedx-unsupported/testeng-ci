# pylint: disable=too-few-public-methods

""" Provides Access to the GitHub API """

from release import get_token
import requests
from requests.auth import AuthBase


class RequestFailed(Exception):
    """ Exception indicating a network request failed """
    def __init__(self, response):
        payload = {
            "url": response.url,
            "code": response.status_code,
            "response": response.content
        }
        super(RequestFailed, self).__init__(payload)
        self.response = response


class TokenAuth(AuthBase):
    """
    Authorization method for requests library supporting github OAuth tokens
    """
    def __init__(self, token):
        self.token = token

    def __call__(self, request):
        request.headers["Authorization"] = "token %s" % self.token
        return request


class GithubApi(object):
    """ Manages requests to the GitHub api for a given org/repo """

    def __init__(self, org, repo, token=None):
        self.token = token or get_token.get_token()
        self.org = org
        self.repo = repo

    def _method(self, path, maker, success_code=200):
        """ Creates a new network request and returns the result """
        url = ("https://api.github.com/%s" % path).format(
            repo=self.repo, org=self.org
        )
        auth = TokenAuth(self.token)
        response = maker(url, auth)
        if response.status_code != success_code:
            raise RequestFailed(response)
        return response.json()

    def _get(self, path):
        """ Creates a new get request and returns the result """
        maker = lambda url, auth: requests.get(url, auth=auth)
        return self._method(path, maker)

    def _post(self, path, args):
        """ Creates a new post request and returns the result """
        maker = lambda url, auth: requests.post(url, json=args, auth=auth)
        return self._method(path, maker, success_code=201)

    def commit_statuses(self, commit_sha):
        """ Returns all the known statuses for a given commit """
        path = "repos/{org}/{repo}/commits/%s/statuses" % commit_sha
        return self._get(path)

    def commits(self):
        """ Returns the top commits for a repo """
        path = "repos/{org}/{repo}/commits"
        return self._get(path)

    def create_branch(self, branch_name, sha):
        """ Creates a new branch based off an existing sha """
        path = "repos/{org}/{repo}/git/refs"
        payload = {
            "ref": "refs/heads/%s" % branch_name,
            "sha": sha
        }
        return self._post(path, payload)

    def create_pull_request(
            self,
            branch_name,
            base="release",
            title="",
            body=""):
        """ Creates a new pull request from a branch """
        path = "repos/{org}/{repo}/pulls"
        payload = {
            "title": title,
            "body": body,
            "head": branch_name,
            "base": base
        }
        return self._post(path, payload)
