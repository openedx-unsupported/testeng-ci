"""
Provides a way to get a github token from disk
or from the calling environment.

If no token is available then it prompts the user to create one
and saves it to disk.
"""
from __future__ import print_function

import os

SAVED_TOKEN_PATH = os.path.expanduser("~/.edx-release")

# Token when passing via environment variable
EDX_RELEASE_GITHUB_TOKEN = "EDX_RELEASE_GITHUB_TOKEN"


class EmptyToken(Exception):
    """ Indicates that a token was found on disk, but it wasn't valid """
    pass


def _fetch_github_token():
    """ Gets a github token from the user and saves it to ~/.edx-release """
    print(
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


def get_token():
    """
    Returns the users github token if available.
    Prompting them if necessary
    """
    # first, check the environment
    token = os.getenv(EDX_RELEASE_GITHUB_TOKEN)
    if token:
        print("Found token in environment")
        return token
    # then, check if we've saved one to a dot file
    try:
        token = open(SAVED_TOKEN_PATH).read()
        if not token or len(token) == 0:
            raise EmptyToken()

        print("Read saved token")
        return token
    except (IOError, EmptyToken):
        # No or invalid dot file. Try next strategy
        pass

    # else require the user to make one
    return _fetch_github_token()
