import base64
import json
import os
from unittest import TestCase

from botocore.vendored.requests import Response
from mock import patch, Mock

from ..process_webhooks import _send_message, _add_gh_header
from ..process_webhooks import _get_target_url, _get_target_queue
from ..process_webhooks import lambda_handler, _is_from_queue


class ProcessWebhooksTestCase(TestCase):
    headers = {
        'Content-Type': 'application/json',
        'X-GitHub-Event': ''
    }

    @patch.dict(os.environ, {'TARGET_URL': 'http://www.example.com'})
    def test_get_target_url_pr(self):
        self.headers['X-GitHub-Event'] = 'pull_request'
        url = _get_target_url(self.headers)
        self.assertEqual(url, 'http://www.example.com/ghprbhook/')

    @patch.dict(os.environ, {'TARGET_URL': 'http://www.example.com'})
    def test_get_target_url_comment(self):
        self.headers['X-GitHub-Event'] = 'issue_comment'
        url = _get_target_url(self.headers)
        self.assertEqual(url, 'http://www.example.com/ghprbhook/')

    @patch.dict(os.environ, {'TARGET_URL': 'http://www.example.com'})
    def test_get_target_url_push(self):
        self.headers['X-GitHub-Event'] = 'push'
        url = _get_target_url(self.headers)
        self.assertEqual(url, 'http://www.example.com/github-webhook/')

    @patch.dict(os.environ, {'TARGET_URL': 'http://www.example.com'})
    def test_get_target_url_ping(self):
        self.headers['X-GitHub-Event'] = 'ping'
        url = _get_target_url(self.headers)
        self.assertEqual(url, None)

    @patch.dict(os.environ, {'TARGET_URL': 'http://www.example.com'})
    def test_get_target_url_error(self):
        self.headers['X-GitHub-Event'] = 'status'
        with self.assertRaises(StandardError):
            url = _get_target_url(self.headers)

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

    @patch.dict(os.environ, {'TARGET_QUEUE': 'queue_name'})
    def test_get_target_queue(self):
        queue = _get_target_queue()
        self.assertEqual(queue, 'queue_name')

    def test_is_from_queue_true(self):
        event = {
            'from_queue': 'True'
        }
        from_queue = _is_from_queue(event)
        self.assertEqual(from_queue, True)

    def test_is_from_queue_false(self):
        event = {
            'from_queue': 'False'
        }
        from_queue = _is_from_queue(event)
        self.assertEqual(from_queue, False)


class ProcessWebhooksRequestTestCase(TestCase):
    @staticmethod
    def mock_response(status_code):
        response = Response()
        response.status_code = status_code
        return response

    def test_send_message_success(self):
        with patch(
            'process_webhooks.process_webhooks.post',
            return_value=self.mock_response(200)
        ):
            response = _send_message('http://www.example.com', None, None)
            self.assertIsNotNone(response)
            self.assertEqual(response.status_code, 200)

    def test_send_message_error(self):
        with patch(
            'process_webhooks.process_webhooks.post',
            return_value=self.mock_response(500)
        ):
            with self.assertRaises(StandardError):
                response = _send_message('http://www.example.com', None, None)
                self.assertEqual(response.message, '500 Server Error: None')


class LambdaHandlerTestCase(TestCase):
    event = {
        'spigot_state': '',
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

    @patch('process_webhooks.process_webhooks._get_target_url',
           return_value='http://www.example.com/endpoint/')
    @patch('process_webhooks.process_webhooks._send_message',
           return_value={})
    def test_lambda_handler_to_target(self, send_msg_mock, _url_mock):
        self.event['spigot_state'] = 'ON'
        lambda_handler(self.event, None)
        send_msg_mock.assert_called_with(
            'http://www.example.com/endpoint/',
            self.event.get('body'),
            {'Content-Type': 'application/json', 'X-GitHub-Event': u'ping'}
        )

    @patch('process_webhooks.process_webhooks._get_target_url',
           return_value='http://www.example.com/endpoint/')
    @patch('process_webhooks.process_webhooks._send_message',
           side_effect=StandardError("Error!"))
    @patch('process_webhooks.process_webhooks._is_from_queue',
           return_value=False)
    @patch('process_webhooks.process_webhooks._get_target_queue',
           return_value='queue_name')
    @patch('process_webhooks.process_webhooks._send_to_queue',
           return_value={})
    def test_lambda_handler_to_target_error(
        self, send_queue_mock, _queue_mock,
        _from_queue_mock, send_msg_mock, _url_mock
    ):
        self.event['spigot_state'] = 'ON'
        with self.assertRaises(StandardError):
            lambda_handler(self.event, None)

        send_msg_mock.assert_called_with(
            'http://www.example.com/endpoint/',
            self.event.get('body'),
            {'Content-Type': 'application/json', 'X-GitHub-Event': u'ping'}
        )
        send_queue_mock.assert_called_with(
            self.event,
            'queue_name'
        )

    @patch('process_webhooks.process_webhooks._get_target_url',
           return_value=None)
    @patch('process_webhooks.process_webhooks._send_message',
           return_value={})
    def test_lambda_handler_ping(self, send_msg_mock, _url_mock):
        self.event['spigot_state'] = 'ON'
        lambda_handler(self.event, None)
        assert not send_msg_mock.called

    @patch('process_webhooks.process_webhooks._get_target_queue',
           return_value='queue_name')
    @patch('process_webhooks.process_webhooks._is_from_queue',
           return_value=False)
    @patch('process_webhooks.process_webhooks._send_to_queue',
           return_value={})
    def test_lambda_handler_to_queue(
        self, send_queue_mock, _from_queue_mock, _queue_mock
    ):
        self.event['spigot_state'] = 'OFF'
        lambda_handler(self.event, None)
        send_queue_mock.assert_called_with(
            self.event,
            'queue_name'
        )

    @patch('process_webhooks.process_webhooks._get_target_queue',
           return_value='queue_name')
    @patch('process_webhooks.process_webhooks._is_from_queue',
           return_value=True)
    @patch('process_webhooks.process_webhooks._send_to_queue',
           return_value={})
    def test_lambda_handler_to_queue_from_queue(
        self, send_queue_mock, _from_queue_mock, _queue_mock
    ):
        self.event['spigot_state'] = 'OFF'
        with self.assertRaises(StandardError):
            lambda_handler(self.event, None)
        assert not send_queue_mock.called
