"""
A class for working with the build info returned from the jenkins job API
"""


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
            for p in action_parameters:
                if p.get('name') == u'ghprbActualCommitAuthorEmail':
                    author = p.get('value')
                if p.get('name') == u'ghprbPullId':
                    pr_id = p.get('value')

        self.author = author
        self.pr_id = pr_id
