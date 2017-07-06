import base64
import json
import os
from unittest import TestCase

from botocore.vendored.requests import Response
from mock import patch, Mock

from ..process_webhooks import _send_message, _process_results_for_failures
from ..process_webhooks import _add_gh_header, _get_target_urls
from ..process_webhooks import _get_target_queue, lambda_handler
from ..process_webhooks import _is_from_queue


class ProcessWebhooksTestCase(TestCase):
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

    def test_process_results_for_failures(self):
        data = [
            {'response': Mock()},
            {'exception': Mock()},
            {'response': Mock()}
        ]
        result = _process_results_for_failures(data)
        self.assertEqual(result, {'failure': 1, 'success': 2})


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
            result = _send_message('http://www.example.com', None, None)
            response = result.get('response')
            self.assertIsNotNone(response)
            self.assertEqual(response.status_code, 200)
            exception = result.get('exception')
            self.assertIsNone(exception)

    def test_send_message_error(self):
        with patch(
            'process_webhooks.process_webhooks.post',
            return_value=self.mock_response(500)
        ):
            result = _send_message('http://www.example.com', None, None)
            response = result.get('response')
            self.assertIsNone(response)
            exception = result.get('exception')
            self.assertEqual(exception.message, '500 Server Error: None')


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

    @patch('process_webhooks.process_webhooks._get_target_urls',
           return_value=['http://www.example.com'])
    @patch('process_webhooks.process_webhooks._send_message',
           return_value={})
    def test_lambda_handler_to_target(self, send_msg_mock, _url_mock):
        self.event['spigot_state'] = 'ON'
        lambda_handler(self.event, None)
        send_msg_mock.assert_called_with(
            'http://www.example.com',
            self.event.get('body'),
            {'Content-Type': 'application/json', 'X-GitHub-Event': u'ping'}
        )

    @patch('process_webhooks.process_webhooks._get_target_urls',
           return_value=['http://www.example.com'])
    @patch('process_webhooks.process_webhooks._send_message',
           return_value={})
    @patch('process_webhooks.process_webhooks._is_from_queue',
           return_value=False)
    @patch('process_webhooks.process_webhooks._get_target_queue',
           return_value='queue_name')
    @patch('process_webhooks.process_webhooks._process_results_for_failures',
           return_value={'failure': 'exception'})
    @patch('process_webhooks.process_webhooks._send_to_queue',
           return_value={})
    def test_lambda_handler_to_target_error(
        self, send_queue_mock, _results_mock, _queue_mock,
        _from_queue_mock, send_msg_mock, _url_mock
    ):
        self.event['spigot_state'] = 'ON'
        with self.assertRaises(StandardError):
            lambda_handler(self.event, None)

        send_msg_mock.assert_called_with(
            'http://www.example.com',
            self.event.get('body'),
            {'Content-Type': 'application/json', 'X-GitHub-Event': u'ping'}
        )
        send_queue_mock.assert_called_with(
            self.event,
            'queue_name'
        )

    @patch('process_webhooks.process_webhooks._get_target_queue',
           return_value='queue_name')
    @patch('process_webhooks.process_webhooks._is_from_queue',
           return_value=False)
    @patch('process_webhooks.process_webhooks._process_results_for_failures',
           return_value={'failure': 'exception'})
    @patch('process_webhooks.process_webhooks._send_to_queue',
           return_value={})
    def test_lambda_handler_to_queue(
        self, send_queue_mock, _results_mock, _from_queue_mock, _queue_mock
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
    @patch('process_webhooks.process_webhooks._process_results_for_failures',
           return_value={'failure': 'exception'})
    @patch('process_webhooks.process_webhooks._send_to_queue',
           return_value={})
    def test_lambda_handler_to_queue_from_queue(
        self, send_queue_mock, _results_mock, _from_queue_mock, _queue_mock
    ):
        self.event['spigot_state'] = 'OFF'
        with self.assertRaises(StandardError):
            lambda_handler(self.event, None)
        assert not send_queue_mock.called
