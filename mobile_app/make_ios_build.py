"""
Invoke this script to kick off a new ios build
"""

import logging
import sys

from mobile_app.make_build import make_build

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def make_ios_build():
    """
    Kicks off a new ios app build, asking the user a few
    additional questions
    """
    make_build(
        "git@github.com:edx/edx-app-ios.git",
        "git@github.com:edx/edx-app-build-ios.git"
    )

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(message)s',
        stream=sys.stdout,
        level=logging.INFO
    )
    make_ios_build()
