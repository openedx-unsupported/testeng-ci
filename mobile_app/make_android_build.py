"""
Invoke this script to kick off a new android build
"""

import logging
import sys

from mobile_app.make_build import make_build

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def make_android_build():
    """
    Kicks off a new android app build, asking the user a few
    additional questions
    """
    make_build(
        "https://github.com/edx/edx-app-android",
        "https://github.com/edx/edx-app-build-android"
    )

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(message)s',
        stream=sys.stdout,
        level=logging.INFO
    )
    make_android_build()
