import base64
import json
import os
from unittest import TestCase

from botocore.vendored.requests import Response
from mock import patch, Mock

from ..webhook_processor import _send_message, _process_results_for_failures
from ..webhook_processor import _verify_data, _add_gh_header, _get_target_urls
from ..webhook_processor import _get_num_tries, _parse_executables_for_builds
from ..webhook_processor import _get_jobs_list, _parse_hook_for_testing_info
from ..webhook_processor import _builds_contain_tests
from ..webhook_processor import _get_running_builds, _get_queued_builds
from ..webhook_processor import lambda_handler
from ..constants import *


class WebhookProcessorTestCase(TestCase):
    def test_verify_data(self):
        test_data = {'foo': 'bar'}
        verified_data = _verify_data(json.dumps(test_data))
        self.assertEqual(verified_data, test_data)

    def test_verify_data_exception(self):
        test_data = 'foo'
        with self.assertRaises(ValueError):
            _verify_data(test_data)

    def test_add_gh_header(self):
        gh_header = {'X-GitHub-Event': 'push'}
        test_data = {'headers': gh_header}
        headers = _add_gh_header(test_data, {})
        self.assertEqual(headers, gh_header)

    def test_add_gh_header_exception(self):
        gh_header = {}
        test_data = {'headers': gh_header}
        with self.assertRaises(ValueError):
            _add_gh_header(test_data, {})

    @patch.dict(os.environ, {'TARGET_URLS': 'http://www.example.com/webhooks'})
    def test_get_target_urls_single(self):
        urls = _get_target_urls()
        self.assertEqual(urls, ['http://www.example.com/webhooks'])

    @patch.dict(
        os.environ,
        {'TARGET_URLS': 'http://www.a.com/foo,http://www.b.com/bar'}
    )
    def test_get_target_urls_multiple(self):
        urls = _get_target_urls()
        self.assertEqual(urls, ['http://www.a.com/foo',
                                'http://www.b.com/bar'])

    @patch.dict(os.environ, {'NUM_TRIES': '3'})
    def test_num_tries(self):
        num_tries = _get_num_tries()
        self.assertEqual(num_tries, 3)

    @patch.dict(os.environ, {'NUM_TRIES': 'notanint'})
    def test_invalid_num_tries(self):
        with self.assertRaises(StandardError):
            num_tries = _get_num_tries()

    def test_process_results_for_failures(self):
        data = [
            {'response': Mock()},
            {'exception': Mock()},
            {'response': Mock()}
        ]
        result = _process_results_for_failures(data)
        self.assertEqual(result, {'failure': 1, 'success': 2})


class WebhookProcessorRequestTestCase(TestCase):
    @staticmethod
    def mock_response(status_code):
        response = Response()
        response.status_code = status_code
        return response

    def test_send_message_success(self):
        with patch(
            'webhook_processor.webhook_processor.post',
            return_value=self.mock_response(200)
        ):
            result = _send_message('http://www.example.com', None, None)
            response = result.get('response')
            self.assertIsNotNone(response)
            self.assertEqual(response.status_code, 200)
            exception = result.get('exception')
            self.assertIsNone(exception)

    def test_send_message_error(self):
        with patch(
            'webhook_processor.webhook_processor.post',
            return_value=self.mock_response(500)
        ):
            result = _send_message('http://www.example.com', None, None)
            response = result.get('response')
            self.assertIsNone(response)
            exception = result.get('exception')
            self.assertEqual(exception.message, '500 Server Error: None')


class JenkinsRetryTestCase(TestCase):
    def test_parse_executables_for_builds(self):
        data = {
            'actions': [{
                'parameters': [{
                    'name': 'sha1',
                    'value': '12345'
                }]
            }],
            'url': 'https://build.testeng.edx.org'
                   '/job/edx-platform-bokchoy-pr/1234'
        }
        build_status = "running"

        expected_response = [{
            "job_name": "edx-platform-bokchoy-pr", "sha": "12345"
        }]
        actual_response = _parse_executables_for_builds(data, build_status)
        self.assertEqual(expected_response, actual_response)

    def test_get_jobs_list(self):
        platform_master_pr_jobs_list = \
            _get_jobs_list('edx-platform', 'master', 'pull_request', False)
        self.assertEqual(
            platform_master_pr_jobs_list, EDX_PLATFORM_PR
        )
        platform_master_merge_jobs_list = \
            _get_jobs_list('edx-platform', 'master', 'pull_request', True)
        self.assertEqual(
            platform_master_merge_jobs_list, EDX_PLATFORM_MASTER
        )

        platform_eucalyptus_pr_jobs_list = \
            _get_jobs_list('edx-platform', 'eucalyptus', 'pull_request', False)
        self.assertEqual(
            platform_eucalyptus_pr_jobs_list, EDX_PLATFORM_EUCALYPTUS_PR
        )
        platform_eucalyptus_merge_jobs_list = \
            _get_jobs_list('edx-platform', 'eucalyptus', 'pull_request', True)
        self.assertEqual(
            platform_eucalyptus_merge_jobs_list, EDX_PLATFORM_EUCALYPTUS_MASTER
        )

        platform_ficus_pr_jobs_list = \
            _get_jobs_list('edx-platform', 'ficus', 'pull_request', False)
        self.assertEqual(
            platform_ficus_pr_jobs_list, EDX_PLATFORM_FICUS_PR
        )
        platform_ficus_merge_jobs_list = \
            _get_jobs_list('edx-platform', 'ficus', 'pull_request', True)
        self.assertEqual(
            platform_ficus_merge_jobs_list, EDX_PLATFORM_FICUS_MASTER
        )

        platform_private_pr_jobs_list = \
            _get_jobs_list('edx-platform-private', '', 'pull_request', False)
        self.assertEqual(
            platform_private_pr_jobs_list, EDX_PLATFORM_PRIVATE_PR
        )
        platform_private_merge_jobs_list = \
            _get_jobs_list('edx-platform-private', '', 'pull_request', True)
        self.assertEqual(
            platform_private_merge_jobs_list, EDX_PLATFORM_PRIVATE_MASTER
        )

        e2e_pr_jobs_list = \
            _get_jobs_list('edx-e2e-tests', '', 'pull_request', False)
        self.assertEqual(
            e2e_pr_jobs_list, EDX_E2E_PR
        )

        empy_jobs_list = \
            _get_jobs_list('dummy_repo', '', 'pull_request', False)
        self.assertEqual(
            empy_jobs_list, []
        )

    @patch('webhook_processor.webhook_processor._get_jobs_list',
           return_value={})
    def test_parse_hook_with_master_open_pr(self, jobs_list_mock):
        data = {
            'action': 'opened',
            'pull_request': {
                'head': {
                    'sha': '12345',
                },
                'base': {
                    'ref': 'master',
                    'repo': {
                        'name': 'edx-platform'
                    }
                },
                'merged': False
            }
        }
        event_type = 'pull_request'
        sha, _ = _parse_hook_for_testing_info(data, event_type)
        self.assertEqual(sha, '12345')
        jobs_list_mock.assert_called_with(
            'edx-platform',
            'master',
            'pull_request',
            False
        )

    @patch('webhook_processor.webhook_processor._get_jobs_list',
           return_value={})
    def test_parse_hook_with_eucalyptus_open_pr(self, jobs_list_mock):
        data = {
            'action': 'opened',
            'pull_request': {
                'head': {
                    'sha': '12345',
                },
                'base': {
                    'ref': 'open-release/eucalyptus.master',
                    'repo': {
                        'name': 'edx-platform'
                    }
                },
                'merged': False
            }
        }
        event_type = 'pull_request'
        sha, _ = _parse_hook_for_testing_info(data, event_type)
        self.assertEqual(sha, '12345')
        jobs_list_mock.assert_called_with(
            'edx-platform',
            'eucalyptus',
            'pull_request',
            False
        )

    @patch('webhook_processor.webhook_processor._get_jobs_list',
           return_value={})
    def test_parse_hook_with_ficus_open_pr(self, jobs_list_mock):
        data = {
            'action': 'opened',
            'pull_request': {
                'head': {
                    'sha': '12345',
                },
                'base': {
                    'ref': 'open-release/ficus.master',
                    'repo': {
                        'name': 'edx-platform'
                    }
                },
                'merged': False
            }
        }
        event_type = 'pull_request'
        sha, _ = _parse_hook_for_testing_info(data, event_type)
        self.assertEqual(sha, '12345')
        jobs_list_mock.assert_called_with(
            'edx-platform',
            'ficus',
            'pull_request',
            False
        )

    @patch('webhook_processor.webhook_processor._get_jobs_list',
           return_value={})
    def test_parse_hook_with_merge_pr(self, jobs_list_mock):
        data = {
            'action': 'closed',
            'pull_request': {
                'base': {
                    'ref': 'master',
                    'repo': {
                        'name': 'edx-platform'
                    }
                },
                'merge_commit_sha': '67890',
                'merged': True
            }
        }
        event_type = 'pull_request'
        sha, _ = _parse_hook_for_testing_info(data, event_type)
        self.assertEqual(sha, '67890')
        jobs_list_mock.assert_called_with(
            'edx-platform',
            'master',
            'pull_request',
            True
        )

    @patch('webhook_processor.webhook_processor._get_jobs_list',
           return_value={})
    def test_parse_hook_with_closed_pr(self, jobs_list_mock):
        data = {
            'action': 'closed',
            'pull_request': {
                'base': {
                    'ref': 'master',
                    'repo': {
                        'name': 'edx-platform'
                    }
                },
                'merge_commit_sha': '67890',
                'merged': False
            }
        }
        event_type = 'pull_request'
        sha, jobs_list = _parse_hook_for_testing_info(data, event_type)
        self.assertEqual(sha, None)
        self.assertEqual(jobs_list, None)
        jobs_list_mock.assert_not_called()

    @patch('webhook_processor.webhook_processor._get_jobs_list',
           return_value={})
    def test_parse_hook_with_non_pr(self, jobs_list_mock):
        data = {
            'body': {
                'zen': 'Non-blocking is better than blocking.',
                'hook_id': 12341234,
                'hook': {
                    'type': 'Repository',
                    'id': 98765432,
                    'events': ['issue_comment', 'pull_request']
                },
                'repository': {'id': 12341234, 'name': 'foo'},
                'sender': {'id': 12345678},
            },
            'headers': {'X-GitHub-Event': 'ping'}
        }
        event_type = 'ping'
        sha, jobs_list = _parse_hook_for_testing_info(data, event_type)
        self.assertEqual(sha, None)
        self.assertEqual(jobs_list, None)
        jobs_list_mock.assert_not_called()

    def test_builds_contain_tests_true(self):
        builds = [{
            'job_name': 'edx-platform-bok-choy-pr',
            'sha': '12345'
        }, {
            'job_name': 'edx-platform-accessibility-pr',
            'sha': '12345'
        }, {
            'job_name': 'edx-platform-js-pr',
            'sha': '12345'
        }, {
            'job_name': 'edx-platform-lettuce-pr',
            'sha': '12345'
        }, {
            'job_name': 'edx-platform-python-unittests-pr',
            'sha': '12345'
        }, {
            'job_name': 'edx-platform-quality-pr',
            'sha': '12345'
        }]
        sha = '12345'
        jobs_list = EDX_PLATFORM_PR

        self.assertEqual(True, _builds_contain_tests(builds, sha, jobs_list))

    def test_builds_contain_tests_false(self):
        builds = [{
            'job_name': 'edx-platform-bok-choy-pr',
            'sha': '56789'
        }, {
            'job_name': 'edx-platform-accessibility-pr',
            'sha': '12345'
        }, {
            'job_name': 'edx-platform-js-pr',
            'sha': '12345'
        }, {
            'job_name': 'edx-platform-lettuce-pr',
            'sha': '12345'
        }, {
            'job_name': 'edx-platform-python-unittests-pr',
            'sha': '12345'
        }, {
            'job_name': 'edx-platform-quality-pr',
            'sha': '12345'
        }]
        sha = '12345'
        jobs_list = EDX_PLATFORM_PR

        self.assertEqual(False, _builds_contain_tests(builds, sha, jobs_list))

    def test_builds_contain_tests_empty(self):
        builds = []
        sha = '12345'
        jobs_list = []

        self.assertEqual(True, _builds_contain_tests(builds, sha, jobs_list))

    @staticmethod
    def mock_running_response():
        data = {
            'computer': [{
                'executors': [{
                    'currentExecutable': {
                        'actions': [{
                            'parameters': [{
                                'name': 'sha1',
                                'value': '12345'
                            }]
                        }],
                        'url': 'https://build.testeng.edx.org'
                               '/job/edx-platform-bokchoy-pr/1234'
                        }
                }],
                'oneOffExecutors': []
            }]
        }
        return data

    @patch('webhook_processor.webhook_processor.get',
           return_value=Response())
    def test_get_running_builds(self, json_mock):
        with patch(
            'botocore.vendored.requests.models.Response.json',
            return_value=self.mock_running_response()
        ):
            expected_response = [
                {"job_name": "edx-platform-bokchoy-pr", "sha": "12345"}
            ]

            url = 'https://www.jenkins.org'
            username = 'username'
            token = 'password'
            actual_response = _get_running_builds(url, username, token)
            self.assertEqual(expected_response, actual_response)


class LambdaHandlerTestCase(TestCase):
    @patch('webhook_processor.webhook_processor._get_num_tries',
           return_value=3)
    @patch('webhook_processor.webhook_processor._get_target_urls',
           return_value=['http://www.example.com'])
    @patch('webhook_processor.webhook_processor._send_message',
           return_value={})
    def test_lambda_handler(self, send_msg_mock, _url_mock, _num_tries_mock):
        data = {
            'body': {
                'zen': 'Non-blocking is better than blocking.',
                'hook_id': 12341234,
                'hook': {
                    'type': 'Repository',
                    'id': 98765432,
                    'events': ['issue_comment', 'pull_request']
                },
                'repository': {'id': 12341234, 'name': 'foo'},
                'sender': {'id': 12345678},
            },
            'headers': {'X-GitHub-Event': 'ping'}
        }

        event = {
            'Records': [{
                'kinesis': {
                    'SequenceNumber': 'n',
                    'ApproximateArrivalTimestamp': 12345,
                    'data': base64.b64encode(json.dumps(data)),
                    'PartitionKey': '1'
                }
            }],
            'NextShardIterator': 'abc',
            'MillisBehindLatest': 0
        }

        lambda_handler(event, None)
        data.pop('headers')
        send_msg_mock.assert_called_with(
            'http://www.example.com',
            data.get('body'),
            {'Content-Type': 'application/json', 'X-GitHub-Event': u'ping'}
        )

    @patch('webhook_processor.webhook_processor._get_num_tries',
           return_value=3)
    @patch('webhook_processor.webhook_processor._get_target_urls',
           return_value=[
               'https://build.testeng.edx.org',
               'https://www.notjenkins.com'
           ])
    @patch('webhook_processor.webhook_processor._send_message',
           return_value={})
    @patch('webhook_processor.webhook_processor._parse_hook_for_testing_info',
           return_value=('12345', ['edx-platform-accessibility-pr']))
    @patch('webhook_processor.webhook_processor._all_tests_triggered',
           side_effect=[False, False, True])
    def test_lambda_handler_retry(
        self, tests_trig_mock, testing_info_mock, send_msg_mock,
        _url_mock, _num_tries_mock
    ):
        data = {
            'body': {
                'action': 'opened',
                'pull_request': {
                    'head': {
                        'sha': '12345',
                    },
                    'base': {
                        'ref': 'master',
                        'repo': {
                            'name': 'edx-platform'
                        }
                    },
                    'merged': False
                }
            },
            'headers': {'X-GitHub-Event': 'pull_request'}
        }

        event = {
            'Records': [{
                'kinesis': {
                    'SequenceNumber': 'n',
                    'ApproximateArrivalTimestamp': 12345,
                    'data': base64.b64encode(json.dumps(data)),
                    'PartitionKey': '1'
                }
            }],
            'NextShardIterator': 'abc',
            'MillisBehindLatest': 0
        }

        lambda_handler(event, None)

        # one url has no jenkins jobs, and the mock will have the other
        # fail the first 2 times. so ensure 4 total messages sent
        self.assertEqual(send_msg_mock.call_count, 4)
