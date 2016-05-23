"""
A class for working with the build info returned from the jenkins job API
"""
import logging


LOGGER = logging.getLogger(__name__)


class Build(dict):
    """
    A class for working with the build info returned from the jenkins job API

    :Args:
        build (dict): build data from Jenkins
    """
    def __init__(self, build):
        super(Build, self).__init__()
        self.isbuilding = build.get('building')

        author = None
        pr_id = None
        actions = build.get('actions')
        if actions:
            action_parameters = actions[0].get('parameters')
            if action_parameters:
                for param in action_parameters:
                    if param.get('name') == u'ghprbActualCommitAuthorEmail':
                        author = param.get('value')
                    if param.get('name') == u'ghprbPullId':
                        pr_id = param.get('value')
            else:

                LOGGER.debug(
                    "Couldn't find build parameters for build #{}".format(
                        build.get('number')
                    )
                )

        self.author = author
        self.pr_id = pr_id
