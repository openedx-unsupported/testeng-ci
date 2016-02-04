"""
Asks the user for the information needed to trigger a build and then triggers
that build. This is meant to stand in for jenkins/a task runner for
testing or when one is not available.
"""

from collections import namedtuple
import logging
import sys
import uuid

from mobile_app import trigger_build

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

Question = namedtuple("Question", ["prompt", "key", "kind"])

QUESTIONS = [
    Question(
        prompt="Code repo URL",
        key="CODE_REPO",
        kind="environ"
    ),
    Question(
        prompt="Code revision",
        key="CODE_REVISION",
        kind="environ"
    ),
    Question(
        prompt="Config repo URL",
        key="CONFIG_REPO",
        kind="environ"
    ),
    Question(
        prompt="Config revision",
        key="CONFIG_REVISION",
        kind="environ"
    ),
    Question(
        prompt="Config subpath",
        key="CONFIG_PATH",
        kind="environ"
    ),
    Question(
        prompt="Build repo local path",
        key="--trigger-repo-path",
        kind="arg"
    ),
]


def fresh_branch_name():
    """
    Generates a unique name for this build
    """
    return "build-%s" % uuid.uuid4()


def collect_params():
    """
    Asks the user to provide values for a series of variables that can be used
    as input to the trigger_build script

    Returns
        (dict, dict) tuple of (environment variables, command line options)
        that can be sent to the trigger_build script
    """
    environ = {}
    args = []
    for question in QUESTIONS:
        value = raw_input(question.prompt + ": ")
        if question.kind is "environ":
            environ[question.key] = value
        elif question.kind is "arg":
            args += [question.key, value]

    branch_name = fresh_branch_name()
    logger.info("Using branch: %s", branch_name)
    args += ["--branch-name", branch_name]
    return (args, environ)


if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(message)s',
        stream=sys.stdout
    )
    logger.setLevel(logging.INFO)
    trigger_build.run_trigger_build(*collect_params())
