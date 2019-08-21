"""
A class for working with the build info returned from the jenkins job API
"""
from __future__ import absolute_import

import logging


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
        actions = build.get('actions', [])
        ghprb_class_name = u'org.jenkinsci.plugins.ghprb.GhprbParametersAction'

        for action in actions:
            if action.get('_class') == ghprb_class_name:
                action_parameters = action.get('parameters')
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
