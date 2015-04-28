"""
A class for working with the build info returned from the jenkins job API
"""
import logging


logging.basicConfig(format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class Build(dict):
    """
    A class for working with the build info returned from the jenkins job API

    :Args:
        build (dict): build data from Jenkins
    """
    def __init__(self, build):
        self.isbuilding = build.get('building')

        author = None
        pr_id = None
        actions = build.get('actions')
        if actions:
            action_parameters = actions[0].get('parameters')
            if action_parameters:
                for p in action_parameters:
                    if p.get('name') == u'ghprbActualCommitAuthorEmail':
                        author = p.get('value')
                    if p.get('name') == u'ghprbPullId':
                        pr_id = p.get('value')
            else:
                logger.debug(
                    "Couldn't find build parameters for build #{}".format(
                        build.get('number')
                    )
                )

        self.author = author
        self.pr_id = pr_id
