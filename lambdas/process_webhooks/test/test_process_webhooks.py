import base64
import json
import os
from unittest import TestCase

from botocore.vendored.requests import Response
from mock import patch, Mock

from ..process_webhooks import _send_message, _add_gh_header
from ..process_webhooks import _get_target_url, _get_target_queue
from ..process_webhooks import lambda_handler, _is_from_queue
from ..process_webhooks import _get_jobs_list, _parse_hook_for_testing_info
from ..process_webhooks import _parse_executable_for_builds
from ..process_webhooks import _get_running_builds
from ..process_webhooks import _get_triggered_jobs_from_list
from ..process_webhooks import _all_jobs_triggered

from ..constants import *

ping_event = {
    "spigot_state": "",
    "body": {
        "zen": "Non-blocking is better than blocking.",
        "hook_id": 12341234,
        "hook": {
            "type": "Repository",
            "id": 98765432,
            "events": ["issue_comment", "pull_request"]
        },
        "repository": {"id": 12341234, "name": "foo"},
        "sender": {"id": 12345678},
    },
    "headers": {"X-GitHub-Event": "ping"}
}

push_event = {
    "spigot_state": "",
    "body": {
        "ref": "",
        "commits": [
            {
                "id": "2899e87215f3686c2e6ebb10d60c68ed215f182a"
            }
        ],
        "head_commit": {
            "id": "2899e87215f3686c2e6ebb10d60c68ed215f182a"
        },
        "repository": {
            "id": 86592256,
            "name": "edx-platform",
        },
        "pusher": {
            "name": "michaelyoungstrom",
            "email": "myoungstrom@edx.org"
        },
        "sender": {
            "login": "michaelyoungstrom"
        }
    },
    "headers": {"X-GitHub-Event": "push"}
}

pr_event = {
    "spigot_state": "",
    "body": {
        "action": "opened",
        "pull_request": {
            "id": 129919040,
            "user": {
                "login": "michaelyoungstrom",
                "id": 9468017
            },
            "head": {
                "sha": "2aebed50cfda531dd0c0d3916c084fd26d81362f",
                "repo": {
                    "id": 86592256,
                    "name": "pr_repo"
                }
            },
            "base": {
                "ref": "master",
                "sha": "e49b8845ead3a45b8c67c461cf139279e55762c7",
                "repo": {
                    "id": 86592256,
                    "name": "edx-platform",
                }
            },
        },
        "repository": {
            "id": 86592256,
            "name": "pr_repo"
        }
    },
    "headers": {"X-GitHub-Event": "pull_request"}
}


class ProcessWebhooksTestCase(TestCase):
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": ""
    }

    @patch.dict(os.environ, {"TARGET_URL": "http://www.example.com"})
    def test_get_target_url_pr(self):
        self.headers["X-GitHub-Event"] = "pull_request"
        url = _get_target_url(self.headers)
        self.assertEqual(url, "http://www.example.com/ghprbhook/")

    @patch.dict(os.environ, {"TARGET_URL": "http://www.example.com"})
    def test_get_target_url_comment(self):
        self.headers["X-GitHub-Event"] = "issue_comment"
        url = _get_target_url(self.headers)
        self.assertEqual(url, "http://www.example.com/ghprbhook/")

    @patch.dict(os.environ, {"TARGET_URL": "http://www.example.com"})
    def test_get_target_url_push(self):
        self.headers["X-GitHub-Event"] = "push"
        url = _get_target_url(self.headers)
        self.assertEqual(url, "http://www.example.com/github-webhook/")

    @patch.dict(os.environ, {"TARGET_URL": "http://www.example.com"})
    def test_get_target_url_ping(self):
        self.headers["X-GitHub-Event"] = "ping"
        url = _get_target_url(self.headers)
        self.assertEqual(url, None)

    @patch.dict(os.environ, {"TARGET_URL": "http://www.example.com"})
    def test_get_target_url_error(self):
        self.headers["X-GitHub-Event"] = "status"
        with self.assertRaises(StandardError):
            url = _get_target_url(self.headers)

    def test_add_gh_header(self):
        gh_header = {"X-GitHub-Event": "push"}
        test_data = {"headers": gh_header}
        headers = _add_gh_header(test_data, {})
        self.assertEqual(headers, gh_header)

    def test_add_gh_header_exception(self):
        gh_header = {}
        test_data = {"headers": gh_header}
        with self.assertRaises(ValueError):
            _add_gh_header(test_data, {})

    @patch.dict(os.environ, {"TARGET_QUEUE": "queue_name"})
    def test_get_target_queue(self):
        queue = _get_target_queue()
        self.assertEqual(queue, "queue_name")

    def test_is_from_queue_true(self):
        event = {
            "from_queue": "True"
        }
        from_queue = _is_from_queue(event)
        self.assertEqual(from_queue, True)

    def test_is_from_queue_false(self):
        event = {
            "from_queue": "False"
        }
        from_queue = _is_from_queue(event)
        self.assertEqual(from_queue, False)


class JenkinsApiTestCase(TestCase):
    """
    Test methods associated with querying Jenkins
    to verify platform jobs have been triggered.
    """
    def test_get_jobs_list_master(self):
        repository = "edx-platform"
        target = "master"
        event_push = "push"
        event_pull = "pull_request"
        jobs_list_push = _get_jobs_list(repository, target, event_push)
        self.assertEqual(
            jobs_list_push, JOBS_DICT["EDX_PLATFORM_MASTER"]
        )
        jobs_list_pr = _get_jobs_list(repository, target, event_pull)
        self.assertEqual(
            jobs_list_pr, JOBS_DICT["EDX_PLATFORM_PR"]
        )

    def test_get_jobs_list_master_private(self):
        repository = "edx-platform-private"
        target = "master"
        event_push = "push"
        event_pull = "pull_request"
        jobs_list_push = _get_jobs_list(repository, target, event_push)
        self.assertEqual(
            jobs_list_push, JOBS_DICT["EDX_PLATFORM_PRIVATE_MASTER"]
        )
        jobs_list_pr = _get_jobs_list(repository, target, event_pull)
        self.assertEqual(
            jobs_list_pr, JOBS_DICT["EDX_PLATFORM_PRIVATE_PR"]
        )

    def test_get_jobs_list_ficus(self):
        repository = "edx-platform"
        target = "ficus"
        event_push = "push"
        event_pull = "pull_request"
        jobs_list_push = _get_jobs_list(repository, target, event_push)
        self.assertEqual(
            jobs_list_push, JOBS_DICT["EDX_PLATFORM_FICUS_MASTER"]
        )
        jobs_list_pr = _get_jobs_list(repository, target, event_pull)
        self.assertEqual(
            jobs_list_pr, JOBS_DICT["EDX_PLATFORM_FICUS_PR"]
        )

    def test_get_jobs_list_ginkgo(self):
        repository = "edx-platform"
        target = "ginkgo"
        event_push = "push"
        event_pull = "pull_request"
        jobs_list_push = _get_jobs_list(repository, target, event_push)
        self.assertEqual(
            jobs_list_push, JOBS_DICT["EDX_PLATFORM_GINKGO_MASTER"]
        )
        jobs_list_pr = _get_jobs_list(repository, target, event_pull)
        self.assertEqual(
            jobs_list_pr, JOBS_DICT["EDX_PLATFORM_GINKGO_PR"]
        )

    def test_get_jobs_list_foo(self):
        repository = "foo"
        target = "master"
        event_push = "push"
        event_pull = "pull_request"
        jobs_list_push = _get_jobs_list(repository, target, event_push)
        self.assertEqual(
            jobs_list_push, []
        )
        jobs_list_pr = _get_jobs_list(repository, target, event_pull)
        self.assertEqual(
            jobs_list_pr, []
        )

    @patch("process_webhooks.process_webhooks._get_jobs_list",
           return_value={})
    def test_parse_hook_push_master(self, _jobs_list_mock):
        payload = push_event.get("body")
        payload["ref"] = "refs/heads/master"
        event_type = "push"
        sha, _, target = _parse_hook_for_testing_info(payload, event_type)
        self.assertEqual(sha, "2899e87215f3686c2e6ebb10d60c68ed215f182a")
        self.assertEqual(target, "master")

    @patch("process_webhooks.process_webhooks._get_jobs_list",
           return_value={})
    def test_parse_hook_push_ficus(self, _jobs_list_mock):
        payload = push_event.get("body")
        payload["ref"] = "refs/heads/open-release/ficus.master"
        event_type = "push"
        sha, _, target = _parse_hook_for_testing_info(payload, event_type)
        self.assertEqual(sha, "2899e87215f3686c2e6ebb10d60c68ed215f182a")
        self.assertEqual(target, "ficus")

    @patch("process_webhooks.process_webhooks._get_jobs_list",
           return_value={})
    def test_parse_hook_push_ficus(self, _jobs_list_mock):
        payload = push_event.get("body")
        payload["ref"] = "refs/heads/open-release/ginkgo.master"
        event_type = "push"
        sha, _, target = _parse_hook_for_testing_info(payload, event_type)
        self.assertEqual(sha, "2899e87215f3686c2e6ebb10d60c68ed215f182a")
        self.assertEqual(target, "ginkgo")

    @patch("process_webhooks.process_webhooks._get_jobs_list",
           return_value={})
    def test_parse_hook_pr_master(self, _jobs_list_mock):
        payload = pr_event.get("body")
        payload["pull_request"]["base"]["ref"] = "refs/heads/master"
        event_type = "pull_request"
        sha, _, target = _parse_hook_for_testing_info(payload, event_type)
        self.assertEqual(sha, "2aebed50cfda531dd0c0d3916c084fd26d81362f")
        self.assertEqual(target, "master")

    @patch("process_webhooks.process_webhooks._get_jobs_list",
           return_value={})
    def test_parse_hook_pr_ficus(self, _jobs_list_mock):
        payload = pr_event.get("body")
        payload["pull_request"]["base"]["ref"] = \
            "refs/heads/open-release/ficus.master"
        event_type = "pull_request"
        sha, _, target = _parse_hook_for_testing_info(payload, event_type)
        self.assertEqual(sha, "2aebed50cfda531dd0c0d3916c084fd26d81362f")
        self.assertEqual(target, "ficus")

    @patch("process_webhooks.process_webhooks._get_jobs_list",
           return_value={})
    def test_parse_hook_pr_ficus(self, _jobs_list_mock):
        payload = pr_event.get("body")
        payload["pull_request"]["base"]["ref"] = \
            "refs/heads/open-release/ginkgo.master"
        event_type = "pull_request"
        sha, _, target = _parse_hook_for_testing_info(payload, event_type)
        self.assertEqual(sha, "2aebed50cfda531dd0c0d3916c084fd26d81362f")
        self.assertEqual(target, "ginkgo")

    def test_parse_hook_comment(self):
        sha, _, target = _parse_hook_for_testing_info(None, "issue_comment")
        self.assertEqual(sha, None)
        self.assertEqual(target, None)

    def test_parse_executable_pr_running(self):
        data = {
            "actions": [{
                "parameters": [{
                    "name": "sha1",
                    "value": "12345"
                }]
            }],
            "url": "https://build.testeng.edx.org"
                   "/job/edx-platform-bok-choy-pr/1234"
        }
        build_status = "running"
        event_type = "pull_request"
        target = "master"

        expected_response = [{
            "job_name": "edx-platform-bok-choy-pr", "sha": "12345"
        }]
        actual_response = _parse_executable_for_builds(
            data, build_status, event_type, target, "12345"
        )
        self.assertEqual(expected_response, actual_response)
        empty_response = _parse_executable_for_builds(
            data, build_status, event_type, target, ""
        )
        self.assertEqual(empty_response, [])

    def test_parse_executable_pr_queued(self):
        data = {
            "actions": [{
                "parameters": [{
                    "name": "sha1",
                    "value": "12345"
                }]
            }],
            "task": {
                "name": "edx-platform-bok-choy-pr"
            }
        }
        build_status = "queued"
        event_type = "pull_request"
        target = "master"
        expected_response = [{
            "job_name": "edx-platform-bok-choy-pr", "sha": "12345"
        }]
        actual_response = _parse_executable_for_builds(
            data, build_status, event_type, target, "12345"
        )
        self.assertEqual(expected_response, actual_response)
        empty_response = _parse_executable_for_builds(
            data, build_status, event_type, target, ""
        )
        self.assertEqual(empty_response, [])

    def test_parse_executable_push_running(self):
        data = {
            "actions": [{
                "buildsByBranchName": {
                    "origin/master": {
                        "buildNumber": 40034,
                        "revision": {
                            "SHA1": "12345",
                        }
                    }
                }
            }],
            "url": "https://jenkins.org/job/edx-platform-bok-choy-pr/400/"
        }
        build_status = "running"
        event_type = "push"
        target = "master"

        expected_response = [{
            "job_name": "edx-platform-bok-choy-pr", "sha": "12345"
        }]
        actual_response = _parse_executable_for_builds(
            data, build_status, event_type, target, "12345"
        )
        self.assertEqual(expected_response, actual_response)
        empty_response = _parse_executable_for_builds(
            data, build_status, event_type, target, ""
        )
        self.assertEqual(empty_response, [])

    def test_parse_executable_push_running_ficus(self):
        data = {
            "actions": [{
                "buildsByBranchName": {
                    "refs/heads/open-release/ficus.master": {
                        "buildNumber": 40034,
                        "revision": {
                            "SHA1": "12345",
                        }
                    }
                }
            }],
            "url": "https://build.testeng.edx.org/job/ficus-bok-choy-pr/4/"
        }
        build_status = "running"
        event_type = "push"
        target = "ficus"

        expected_response = [{
            "job_name": "ficus-bok-choy-pr", "sha": "12345"
        }]
        actual_response = _parse_executable_for_builds(
            data, build_status, event_type, target, "12345"
        )
        self.assertEqual(expected_response, actual_response)
        empty_response = _parse_executable_for_builds(
            data, build_status, event_type, target, ""
        )
        self.assertEqual(empty_response, [])

    def test_parse_executable_push_running_ginkgo(self):
        data = {
            "actions": [{
                "buildsByBranchName": {
                    "refs/heads/open-release/ginkgo.master": {
                        "buildNumber": 40034,
                        "revision": {
                            "SHA1": "12345",
                        }
                    }
                }
            }],
            "url": "https://build.testeng.edx.org/job/ginkgo-bok-choy-pr/4/"
        }
        build_status = "running"
        event_type = "push"
        target = "ginkgo"

        expected_response = [{
            "job_name": "ginkgo-bok-choy-pr", "sha": "12345"
        }]
        actual_response = _parse_executable_for_builds(
            data, build_status, event_type, target, "12345"
        )
        self.assertEqual(expected_response, actual_response)
        empty_response = _parse_executable_for_builds(
            data, build_status, event_type, target, ""
        )
        self.assertEqual(empty_response, [])

    def test_parse_executable_push_queued(self):
        data = {
            "actions": [{
                "parameters": [{
                    "name": "sha1",
                    "value": "12345"
                }],
                },
                {
                "causes": [{
                    "upstreamProject": "edx-platform-bok-choy-pr"
                }]
            }]
        }
        build_status = "queued"
        event_type = "push"
        target = "ginkgo"
        expected_response = [{
            "job_name": "edx-platform-bok-choy-pr", "sha": "12345"
        }]
        actual_response = _parse_executable_for_builds(
            data, build_status, event_type, target, "12345"
        )
        self.assertEqual(expected_response, actual_response)

    @staticmethod
    def mock_running_response():
        data = {
            "computer": [{
                "executors": [{
                    "currentExecutable": {
                        "actions": [{
                            "parameters": [{
                                "name": "sha1",
                                "value": "12345"
                            }]
                        }],
                        "url": "https://build.testeng.edx.org"
                               "/job/edx-platform-bokchoy-pr/1234"
                        }
                }],
                "oneOffExecutors": []
            }]
        }
        return data

    @patch("process_webhooks.process_webhooks.get",
           return_value=Response())
    def test_get_running_builds(self, json_mock):
        with patch(
            "botocore.vendored.requests.models.Response.json",
            return_value=self.mock_running_response()
        ):
            expected_response = [
                {"job_name": "edx-platform-bokchoy-pr", "sha": "12345"}
            ]
            url = "https://www.jenkins.org"
            username = "username"
            token = "password"
            actual_response = _get_running_builds(
                url, username, token, "pull_request", "master", "12345"
            )
            self.assertEqual(expected_response, actual_response)

    def test_get_triggered_from_list(self):
        jobs_list = JOBS_DICT["EDX_PLATFORM_PR"]
        builds = [{
            "job_name": "edx-platform-bok-choy-pr",
            "sha": "12345"
        }, {
            "job_name": "edx-platform-accessibility-pr",
            "sha": "12345"
        }, {
            "job_name": "edx-platform-js-pr",
            "sha": "12345"
        }, {
            "job_name": "edx-platform-lettuce-pr",
            "sha": "12345"
        }]
        sha = "12345"
        already_triggered = [
            "edx-platform-quality-pr", "edx-platform-python-unittests-pr"
        ]
        jobs = _get_triggered_jobs_from_list(
            builds, already_triggered, sha, jobs_list
        )
        self.assertEqual(set(jobs), set(jobs_list))

    def test_all_tests_triggered(self):
        triggered_jobs = [
            "edx-platform-quality-pr", "edx-platform-python-unittests-pr",
            "edx-platform-bok-choy-pr", "edx-platform-accessibility-pr",
            "edx-platform-js-pr", "edx-platform-lettuce-pr",
        ]
        all_triggered = _all_jobs_triggered(
            triggered_jobs, JOBS_DICT["EDX_PLATFORM_PR"]
        )
        self.assertEqual(all_triggered, True)
        triggered_jobs.pop()
        all_triggered = _all_jobs_triggered(
            triggered_jobs, JOBS_DICT["EDX_PLATFORM_PR"]
        )
        self.assertEqual(all_triggered, False)


class ProcessWebhooksRequestTestCase(TestCase):
    @staticmethod
    def mock_response(status_code):
        response = Response()
        response.status_code = status_code
        return response

    def test_send_message_success(self):
        with patch(
            "process_webhooks.process_webhooks.post",
            return_value=self.mock_response(200)
        ):
            response = _send_message("http://www.example.com", None, None)
            self.assertIsNotNone(response)
            self.assertEqual(response.status_code, 200)

    def test_send_message_error(self):
        with patch(
            "process_webhooks.process_webhooks.post",
            return_value=self.mock_response(500)
        ):
            with self.assertRaises(StandardError):
                response = _send_message("http://www.example.com", None, None)
                self.assertEqual(response.message, "500 Server Error: None")


class LambdaHandlerTestCase(TestCase):
    @patch("process_webhooks.process_webhooks._get_target_url",
           return_value="http://www.example.com/endpoint/")
    @patch("process_webhooks.process_webhooks._send_message",
           return_value={})
    @patch("process_webhooks.process_webhooks._parse_hook_for_testing_info",
           return_value=("12345", JOBS_DICT['EDX_PLATFORM_MASTER'], "master"))
    @patch("process_webhooks.process_webhooks._get_all_triggered_builds",
           return_value={})
    @patch("process_webhooks.process_webhooks._get_triggered_jobs_from_list",
           return_value=list(JOBS_DICT['EDX_PLATFORM_MASTER']))
    @patch("process_webhooks.process_webhooks._all_jobs_triggered",
           return_value=True)
    def test_lambda_handler_to_target_jobs_list(
        self, all_triggered_mock, _from_list_mock, _get_jobs_mock,
        _parse_hook_mock, send_msg_mock, _url_mock
    ):
        push_event["spigot_state"] = "ON"
        lambda_handler(push_event, None)
        send_msg_mock.assert_called_with(
            "http://www.example.com/endpoint/",
            push_event.get("body"),
            {"Content-Type": "application/json", "X-GitHub-Event": u"push"}
        )
        all_triggered_mock.assert_called_with(
            list(JOBS_DICT['EDX_PLATFORM_MASTER']),
            JOBS_DICT['EDX_PLATFORM_MASTER']
        )

    @patch("process_webhooks.process_webhooks._get_target_url",
           return_value="http://www.example.com/endpoint/")
    @patch("process_webhooks.process_webhooks._send_message",
           return_value={})
    @patch("process_webhooks.process_webhooks._parse_hook_for_testing_info",
           return_value=("12345", ('job1', 'job2'), "master"))
    @patch("process_webhooks.process_webhooks._get_all_triggered_builds",
           return_value={})
    @patch("process_webhooks.process_webhooks._all_jobs_triggered",
           return_value=True)
    def test_lambda_handler_to_target_jobs_list_already_triggered(
        self, all_triggered_mock, _get_jobs_mock,
        _parse_hook_mock, send_msg_mock, _url_mock
    ):
        push_event.update({'already_triggered': ['job1', 'job2']})
        push_event["spigot_state"] = "ON"
        lambda_handler(push_event, None)
        send_msg_mock.assert_called_with(
            "http://www.example.com/endpoint/",
            push_event.get("body"),
            {"Content-Type": "application/json", "X-GitHub-Event": u"push"}
        )
        all_triggered_mock.assert_called_with(
            ['job1', 'job2'],
            ('job1', 'job2')
        )

    @patch("process_webhooks.process_webhooks._get_target_url",
           return_value="http://www.example.com/endpoint/")
    @patch("process_webhooks.process_webhooks._send_message",
           return_value={})
    @patch("process_webhooks.process_webhooks._parse_hook_for_testing_info",
           return_value=("12345", JOBS_DICT['EDX_PLATFORM_MASTER'], "master"))
    @patch("process_webhooks.process_webhooks._get_all_triggered_builds",
           return_value={})
    @patch("process_webhooks.process_webhooks._get_triggered_jobs_from_list",
           return_value=[])
    @patch("process_webhooks.process_webhooks._all_jobs_triggered",
           return_value=False)
    @patch("process_webhooks.process_webhooks._get_target_queue",
           return_value="queue_name")
    @patch("process_webhooks.process_webhooks._send_to_queue",
           return_value=None)
    def test_lambda_handler_to_target_jobs_list_not_triggered(
        self, send_to_queue, _queue_mock, all_triggered_mock,
        _from_list_mock, _get_jobs_mock, _parse_hook_mock,
        send_msg_mock, _url_mock
    ):
        push_event["spigot_state"] = "ON"
        with self.assertRaises(StandardError):
            lambda_handler(push_event, None)
        send_msg_mock.assert_called_with(
            "http://www.example.com/endpoint/",
            push_event.get("body"),
            {"Content-Type": "application/json", "X-GitHub-Event": u"push"}
        )
        all_triggered_mock.assert_called_with(
            [],
            JOBS_DICT['EDX_PLATFORM_MASTER']
        )
        send_to_queue.assert_called_with(push_event, "queue_name")


    @patch("process_webhooks.process_webhooks._get_target_url",
           return_value="http://www.example.com/endpoint/")
    @patch("process_webhooks.process_webhooks._send_message",
           return_value={})
    @patch("process_webhooks.process_webhooks._parse_hook_for_testing_info",
           return_value=(None, [], None))
    def test_lambda_handler_to_target_no_jobs_list(
        self, _parse_hook_mock, send_msg_mock, _url_mock
    ):
        push_event["spigot_state"] = "ON"
        lambda_handler(push_event, None)
        send_msg_mock.assert_called_with(
            "http://www.example.com/endpoint/",
            push_event.get("body"),
            {"Content-Type": "application/json", "X-GitHub-Event": u"push"}
        )

    @patch("process_webhooks.process_webhooks._get_target_url",
           return_value="http://www.example.com/endpoint/")
    @patch("process_webhooks.process_webhooks._send_message",
           side_effect=StandardError("Error!"))
    @patch("process_webhooks.process_webhooks._is_from_queue",
           return_value=False)
    @patch("process_webhooks.process_webhooks._get_target_queue",
           return_value="queue_name")
    @patch("process_webhooks.process_webhooks._send_to_queue",
           return_value={})
    def test_lambda_handler_to_target_error(
        self, send_queue_mock, _queue_mock,
        _from_queue_mock, send_msg_mock, _url_mock
    ):
        push_event["spigot_state"] = "ON"
        with self.assertRaises(StandardError):
            lambda_handler(push_event, None)

        send_msg_mock.assert_called_with(
            "http://www.example.com/endpoint/",
            push_event.get("body"),
            {"Content-Type": "application/json", "X-GitHub-Event": u"push"}
        )
        send_queue_mock.assert_called_with(
            push_event,
            "queue_name"
        )

    @patch("process_webhooks.process_webhooks._get_target_url",
           return_value=None)
    @patch("process_webhooks.process_webhooks._send_message",
           return_value={})
    def test_lambda_handler_ping(self, send_msg_mock, _url_mock):
        ping_event["spigot_state"] = "ON"
        lambda_handler(ping_event, None)
        assert not send_msg_mock.called

    @patch("process_webhooks.process_webhooks._get_target_queue",
           return_value="queue_name")
    @patch("process_webhooks.process_webhooks._is_from_queue",
           return_value=False)
    @patch("process_webhooks.process_webhooks._send_to_queue",
           return_value={})
    def test_lambda_handler_to_queue(
        self, send_queue_mock, _from_queue_mock, _queue_mock
    ):
        push_event["spigot_state"] = "OFF"
        lambda_handler(push_event, None)
        send_queue_mock.assert_called_with(
            push_event,
            "queue_name"
        )

    @patch("process_webhooks.process_webhooks._get_target_queue",
           return_value="queue_name")
    @patch("process_webhooks.process_webhooks._is_from_queue",
           return_value=True)
    @patch("process_webhooks.process_webhooks._send_to_queue",
           return_value={})
    def test_lambda_handler_to_queue_from_queue(
        self, send_queue_mock, _from_queue_mock, _queue_mock
    ):
        push_event["spigot_state"] = "OFF"
        with self.assertRaises(StandardError):
            lambda_handler(push_event, None)
        assert not send_queue_mock.called
