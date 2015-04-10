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


def sample_data(running_builds, not_running_builds):
    """
    Args:
        running_builds: (list of str) A list of PR numbers that have
            running builds. For example, ['1', '1', '2'] indicates
            that there are currently 2 builds running for PR #1 and
            1 build running for PR #2. The last instance of '1' in
            the list will correlate to the currently relevant build.
            The build number will be the array index of the item.
        not_running_builds: (list of str) A list of PR numbers that
            have previously run builds. The build number will be the
            array index of the item plus the length of running_builds.
    Returns:
        Python dict of build data. This is in the format expected to
        be returned by the jenkins api.
    """
    builds = []

    def mktimestamp(minutes_ago):
        first_time = 142009200 * 1000
        build_time = first_time - (minutes_ago * 60000)
        return str(build_time)

    for i in range(0, len(running_builds)):
        builds.append(
            '{"actions" : [{"parameters" :[{"name": "ghprbPullId",'
            '"value" : "' + running_builds[i] + '"}]},{},{}], '
            '"building": true, "number": ' + str(i) +
            ', "timestamp" : ' + mktimestamp(i) + '}'
        )

    for i in range(0, len(not_running_builds)):
        num = i + len(running_builds)
        builds.append(
            '{"actions" : [{"parameters" :[{"name": "ghprbPullId",'
            '"value" : "' + not_running_builds[i] + '"}]},{},{}], '
            '"building": false, "number": ' + str(num)
            + ', "timestamp" : ' + mktimestamp(num) + '}'
        )

    build_data = ''.join([
        '{"builds": [',
        ','.join(builds),
        ']}',
    ])

    return json.loads(build_data)
