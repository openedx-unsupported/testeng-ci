import base64
import json
import os
from unittest import TestCase

from botocore.vendored.requests import Response
from mock import patch, Mock

from ..webhook_processor import _send_message, _process_results_for_failures
from ..webhook_processor import _verify_data, _add_gh_header, _get_target_urls
from ..webhook_processor import lambda_handler


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


class LambdaHandlerTestCase(TestCase):
    @patch('webhook_processor.webhook_processor._get_target_urls',
           return_value=['http://www.example.com'])
    @patch('webhook_processor.webhook_processor._send_message',
           return_value={})
    def test_lambda_handler(self, send_msg_mock, _url_mock):
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
