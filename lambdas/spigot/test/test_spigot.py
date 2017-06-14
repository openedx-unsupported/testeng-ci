import base64
import json
import os
from unittest import TestCase

from botocore.vendored.requests import Response
from mock import patch, Mock

from ..spigot import _send_message, _process_results_for_failures
from ..spigot import _add_gh_header, _get_target_urls, _get_target_queue
from ..spigot import _get_state_from_s3, lambda_handler


class SpigotTestCase(TestCase):
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

    @patch.dict(os.environ, {'TARGET_QUEUE': 'queue_name'})
    def test_get_target_queue(self):
        queue = _get_target_queue()
        self.assertEqual(queue, 'queue_name')

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
            'spigot.spigot.post',
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
            'spigot.spigot.post',
            return_value=self.mock_response(500)
        ):
            result = _send_message('http://www.example.com', None, None)
            response = result.get('response')
            self.assertIsNone(response)
            exception = result.get('exception')
            self.assertEqual(exception.message, '500 Server Error: None')


class LambdaHandlerTestCase(TestCase):
    @patch('spigot.spigot._get_state_from_s3',
           return_value='ON')
    @patch('spigot.spigot._get_target_urls',
           return_value=['http://www.example.com'])
    @patch('spigot.spigot._send_message',
           return_value={})
    def test_lambda_handler_spigot_ON(
        self, send_msg_mock, _url_mock, state_mock
    ):
        event = {
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

        lambda_handler(event, None)
        event.pop('headers')
        send_msg_mock.assert_called_with(
            'http://www.example.com',
            event.get('body'),
            {'Content-Type': 'application/json', 'X-GitHub-Event': u'ping'}
        )

    @patch('spigot.spigot._send_to_queue',
           return_value={})
    @patch('spigot.spigot._get_target_queue',
           return_value='queue_name')
    @patch('spigot.spigot._get_state_from_s3',
           return_value='OFF')
    @patch('spigot.spigot._get_target_urls',
           return_value=['http://www.example.com'])
    @patch('spigot.spigot._send_message',
           return_value={})
    def test_lambda_handler_spigot_OFF(
        self, send_msg_mock, _url_mock,
        state_mock, queue_mock, send_queue_mock
    ):
        event = {
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

        lambda_handler(event, None)
        send_queue_mock.assert_called_with(
            event,
            'queue_name'
        )
