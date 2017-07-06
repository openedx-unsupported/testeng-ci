import base64
import json
import os
from unittest import TestCase

from botocore.vendored.requests import Response
from mock import patch, Mock

from ..send_from_queue import _get_target_queue, _get_api_url
from ..send_from_queue import _delete_from_queue, lambda_handler


class SendFromQueueTestCase(TestCase):
    @patch.dict(os.environ, {'TARGET_QUEUE': 'queue_name'})
    def test_get_target_queue(self):
        queue = _get_target_queue()
        self.assertEqual(queue, 'queue_name')


class LambdaHandlerTestCase(TestCase):
    @staticmethod
    def mock_response(status_code):
        response = Response()
        response.status_code = status_code
        return response

    # Create mock class to represent a queue message
    class mock_message():
        body = json.dumps(
            {
                'body': {
                    'zen': 'Non-blocking is better than blocking.',
                    'hook_id': 12341234,
                    'hook': {
                        'type': 'Repository',
                        'id': 98765432,
                        'events': ['issue_comment', 'pull_request']
                    },
                    'repository': {'id': 12341234, 'name': 'foo'},
                    'sender': {'id': 12345678}
                },
                'headers': {'X-GitHub-Event': 'ping'}
            }
        )

    @patch('send_from_queue.send_from_queue._get_target_queue',
           return_value='queue_name')
    @patch('send_from_queue.send_from_queue._get_queue_object',
           return_value={})
    @patch('send_from_queue.send_from_queue._is_queue_empty',
           return_value=True)
    def test_lambda_handler_empty_queue(
        self, _queue_empty_mock, _queue_object, _queue_mock
    ):
        response = lambda_handler(None, None)
        self.assertEqual(response, "No visible messages in the queue to clear")

    @patch('send_from_queue.send_from_queue._get_target_queue',
           return_value='queue_name')
    @patch('send_from_queue.send_from_queue._get_queue_object',
           return_value={})
    @patch('send_from_queue.send_from_queue._get_api_url',
           return_value='https://api.com')
    @patch('send_from_queue.send_from_queue._is_queue_empty',
           side_effect=[False, False, True])
    @patch('send_from_queue.send_from_queue._get_from_queue',
           return_value=[mock_message()])
    @patch('send_from_queue.send_from_queue._delete_from_queue',
           return_value={})
    def test_lambda_handler_with_queue(
        self, delete_mock, msg_from_queue_mock,
        queue_empty_mock, _api_mock, _queue_object, _queue_mock
    ):
        with patch(
            'send_from_queue.send_from_queue.post',
            return_value=self.mock_response(200)
        ):
            lambda_handler(None, None)
            self.assertEqual(queue_empty_mock.call_count, 3)
            self.assertEqual(msg_from_queue_mock.call_count, 1)
            self.assertEqual(delete_mock.call_count, 1)

    @patch('send_from_queue.send_from_queue._get_target_queue',
           return_value='queue_name')
    @patch('send_from_queue.send_from_queue._get_queue_object',
           return_value={})
    @patch('send_from_queue.send_from_queue._get_api_url',
           return_value='https://api.com')
    @patch('send_from_queue.send_from_queue._is_queue_empty',
           side_effect=[False, False, True])
    @patch('send_from_queue.send_from_queue._get_from_queue',
           return_value=[mock_message()])
    @patch('send_from_queue.send_from_queue._delete_from_queue',
           return_value={})
    def test_lambda_handler_with_queue_error(
        self, _delete_mock, msg_from_queue_mock,
        queue_empty_mock, _api_mock, _queue_object, _queue_mock
    ):
        with patch(
            'send_from_queue.send_from_queue.post',
            return_value=self.mock_response(500)
        ):
            with self.assertRaises(StandardError):
                lambda_handler(None, None)
            self.assertEqual(queue_empty_mock.call_count, 2)
            self.assertEqual(msg_from_queue_mock.call_count, 1)
            assert not _delete_mock.called
