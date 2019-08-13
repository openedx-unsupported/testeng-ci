from unittest import TestCase

import datetime

from mock import patch, Mock

from jenkins.codecov_response_metrics import (
    get_recent_pull_requests,
    get_context_age,
    gather_codecov_metrics
)


class MockRepo(object):

    def __init__(self, full_name, prs):
        self.full_name = full_name
        self.prs = prs

    def get_pulls(self, state, sort, direction):
        return self.prs


class MockPR(object):

    def __init__(self, title, commits=[], age=10000):
        self.title = title
        self.commits = commits
        self.updated_at = datetime.datetime.utcnow() - datetime.timedelta(seconds=age)

    def get_commits(self):
        return self

    @property
    def reversed(self):
        return self.commits[::-1]


class MockCommit(object):

    def __init__(self, combined_status, sha=123):
        self.combined_status = combined_status
        self.sha = sha

    def get_combined_status(self):
        return self.combined_status


class MockCombinedStatus(object):

    def __init__(self, statuses):
        self.statuses = statuses


class MockStatus(object):

    def __init__(self, context, age, state='success'):
        self.context = context
        self.updated_at = datetime.datetime.utcnow() - datetime.timedelta(seconds=age)
        self.state = state


class CodeCovTest(TestCase):

    def test_recent_pull_request(self):

        # pull request in which the HEAD commit has no 'recent' status contexts
        mocked_old_combined_status = MockCombinedStatus(
            [
                MockStatus('A', 1000),
                MockStatus('B', 1000),
                MockStatus('C', 2000)
            ]
        )
        mocked_old_commit = MockCommit(mocked_old_combined_status)
        mocked_old_pr = MockPR('My PR', [None, None, mocked_old_commit])

        # pull request in which at least one status context is 'recent' on
        # the HEAD commit
        mocked_new_combined_status = MockCombinedStatus(
            [
                MockStatus('A', 1000),
                MockStatus('B', 100),
                MockStatus('C', 2000)
            ]
        )
        mocked_new_commit = MockCommit(mocked_new_combined_status)
        mocked_new_pr = MockPR('Test Pr', [None, None, None, mocked_new_commit])

        mocked_repo = MockRepo('mock/repo', [mocked_old_pr, mocked_new_pr])

        recent_pull_requests = get_recent_pull_requests(mocked_repo, 500)
        self.assertEqual(len(recent_pull_requests), 1)
        self.assertEqual(recent_pull_requests[0].title, 'Test Pr')

    def test_context_age_calculation(self):
        mocked_combined_status = MockCombinedStatus(
            [
                MockStatus('A', 10),
                MockStatus('B', 1000),
                MockStatus('C', 500),
                MockStatus('D', 100)
            ]
        )
        posted, context_age, _ = get_context_age(
            mocked_combined_status.statuses, 'D', 'B'
        )
        self.assertTrue(posted)
        self.assertEqual(context_age, 900)

    def test_context_age_calculation_not_present(self):
        mocked_combined_status = MockCombinedStatus(
            [
                MockStatus('A', 10),
                MockStatus('B', 100),
                MockStatus('C', 500)
            ]
        )
        posted, context_age, _ = get_context_age(
            mocked_combined_status.statuses, 'D', 'B'
        )
        self.assertFalse(posted)
        self.assertEqual(context_age, 100)

    def test_trigger_contexts_not_present(self):
        mocked_combined_status_without_triggers = MockCombinedStatus(
            [
                MockStatus('A', 10),
                MockStatus('B', 1000),
                MockStatus('C', 500),
                MockStatus('D', 100)
            ]
        )
        mocked_combined_status_with_triggers = MockCombinedStatus(
            [
                MockStatus('continuous-integration/travis-ci/pr', 2000),
                MockStatus('continuous-integration/travis-ci/push', 1000),
                MockStatus('codecov/patch', 500),
                MockStatus('codecov/project', 100)
            ]
        )
        mocked_commit_1 = MockCommit(
            mocked_combined_status_without_triggers, 1111
        )
        mocked_commit_2 = MockCommit(
            mocked_combined_status_with_triggers, 2222
        )

        mocked_prs = [
            MockPR('pr #1', [None, None, mocked_commit_1]),
            MockPR('pr #2', [None, None, None, mocked_commit_2])
        ]
        mocked_repos = [MockRepo('edx/ecommerce', mocked_prs)]

        metrics = gather_codecov_metrics(mocked_repos, 5000)

        now = datetime.datetime.utcnow().replace(microsecond=0)
        expected_results = [
            {
                'repo': 'edx/ecommerce',
                'pull_request': 'pr #2',
                'commit': 2222,
                'trigger_context_posted_at': str(now - datetime.timedelta(seconds=2000)),
                'codecov_received':  True,
                'codecov_received_after': 1500,
                'context': 'codecov/patch'
            },
            {
                'repo': 'edx/ecommerce',
                'pull_request': 'pr #2',
                'commit': 2222,
                'trigger_context_posted_at': str(now - datetime.timedelta(seconds=1000)),
                'codecov_received':  True,
                'codecov_received_after': 900,
                'context': 'codecov/project'
            }
        ]
        self.assertItemsEqual(metrics, expected_results)
