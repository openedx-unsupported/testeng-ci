import json
import datetime
import functools
from mock import Mock
from requests import Response


def mock_response(status_code, data=None):
    response = Response()
    response.status_code = status_code
    response.json = Mock(return_value=data)
    return response


def mock_utcnow(func):
    class MockDatetime(datetime.datetime):

        @classmethod
        def utcnow(cls):
            return datetime.datetime.utcfromtimestamp(142009200.0)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        olddatetime = datetime.datetime
        datetime.datetime = MockDatetime
        ret = func(*args, **kwargs)
        datetime.datetime = olddatetime
        return ret

    return wrapper


class Pr(object):

    """
    Sample PR dict to use as test data
    """

    def __init__(self, prnum, author='foo@example.com'):
        self.prnum = prnum
        self.author = author

    @property
    def dict(self):
        """
        Return the PR object as a dict
        """
        return self.__dict__


def sample_data(running_builds, not_running_builds):
    """
    Args:
        running_builds: (list of dict) A list of dicts, one for each
            PR with a running build. Each dict has key/value pairs for
            PR number and commit author's email. For example,
            [{'pr': '1', 'author': 'foo@example.com'}, {'pr': '1',
            'author': 'foo@example.com'}, {'pr': '2', 'author':
            'bar@example.com'}] indicates that there are currently
            2 builds running for PR #1 and 1 build running for PR #2.
            (In this example the same author happened to push commits
            twice for PR #1.) The last iterable for PR '1' in the
            list will correlate to the currently relevant build.
            We will use the array index of the item as the build number.
        not_running_builds: (list of dict) A list of dicts for PRs that
            have previously run builds. So that all the build numbers
            are unique, we will use the length of running_builds plus
            the array index of the item as the build number.
    Returns:
        Python dict of build data. This is in the format expected to
        be returned by the jenkins api.
    """
    builds = []

    def mktimestamp(minutes_ago):
        first_time = 142009200 * 1000
        build_time = first_time - (minutes_ago * 60000)
        return build_time

    for i in range(0, len(running_builds)):
        parameters = [
            {'name': 'ghprbPullId', 'value': running_builds[i].get('prnum')},
            {'name': 'ghprbActualCommitAuthorEmail', 'value': running_builds[i].get('author')}
        ]
        actions = [
            {
                '_class': 'org.jenkinsci.plugins.ghprb.GhprbParametersAction',
                'parameters': parameters
            }, {}, {}
        ]
        builds.append({
            'actions': actions,
            'building': True,
            'number': i,
            'timestamp': mktimestamp(i)
        })

    for i in range(0, len(not_running_builds)):
        num = i + len(running_builds)
        parameters = [
            {'name': 'ghprbPullId', 'value': not_running_builds[i].get('prnum')},
            {'name': 'ghprbActualCommitAuthorEmail', 'value': not_running_builds[i].get('author')}
        ]
        actions = [
            {
                '_class': 'org.jenkinsci.plugins.ghprb.GhprbParametersAction',
                'parameters': parameters
            }, {}, {}
        ]
        builds.append({
            'actions': actions,
            'building': False,
            'number': num,
            'timestamp': mktimestamp(num)
        })

    build_data = {'builds': builds}
    return build_data
