"""
Provides a way to get a github token from disk
or from the calling environment.

If no token is available then it prompts the user to create one
and saves it to disk.
"""
from __future__ import print_function

import logging
import os
import sys

from release.github_api import GithubApi, RequestFailed

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SAVED_TOKEN_PATH = os.path.expanduser("~/.edx-release")

# Token when passing via environment variable
EDX_RELEASE_GITHUB_TOKEN = "EDX_RELEASE_GITHUB_TOKEN"


class EmptyToken(Exception):
    """
    Indicates that a token was found on disk, but it wasn't valid
    """
    pass


def _fetch_github_token():
    """
    Gets a github token from the user and saves it to ~/.edx-release

    Returns:
        string: The user entered token

    """
    logger.info(
        """
        You don't have a saved GitHub token.
        You can make one at https://github.com/settings/tokens/new

        Ensure that the "repo", "public_repo", and "repo:status"
        permissions are checked.
        """
    )
    token = raw_input("GitHub Auth Token: ")
    with open(SAVED_TOKEN_PATH, "w") as output:
        output.write(token)
    return token


def _load_token():
    """
    Returns the user's github token if available, prompting them if necessary.

    Returns:
        string: The loaded token.
    """
    # first, check the environment
    token = os.getenv(EDX_RELEASE_GITHUB_TOKEN)
    if token:
        logger.info("Found token in environment")
        return token
    # then, check if we've saved one to a dot file
    try:
        with open(SAVED_TOKEN_PATH) as token_file:
            token = token_file.read()
        if not token:
            raise EmptyToken()

        logger.info("Read saved token")
        return token
    except (IOError, EmptyToken):
        # No or invalid dot file. Try next strategy
        pass
    # else require the user to make one
    token = _fetch_github_token()
    return token


def validate_token(token):
    """
    Validate the token by making a request for the current user.

    Exits if the token could not be validated.

    """
    try:
        api = GithubApi(None, None, token=token)
        user = api.user()
        logger.info("Authenticated {user}".format(user=user['login']))
    except RequestFailed as exception:
        logger.error(
            "Couldn't authenticated on Github. Error: {error}".format(
                error=exception
            )
        )
        # couldn't connect to Github so abort
        sys.exit(1)


def get_token():
    """
    Load the user's github token.

    Loads the user's github token if available and it is valid.
    If they don't have a saved token, it will prompt them to create one
    and enter it.

    Returns:
        string: The loaded token

    """
    token = _load_token()
    validate_token(token)
    return token
