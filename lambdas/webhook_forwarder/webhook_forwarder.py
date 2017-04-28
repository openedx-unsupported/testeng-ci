import json
import base64
import os

import botocore.session

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.info('Loading function')


def lambda_handler(event, context):
    session = botocore.session.get_session()
    kinesis = session.create_client('kinesis')

    stream_name = os.environ.get('STREAM_NAME')
    if not stream_name:
        raise Exception('Environment variable STREAM_NAME was not set')

    try:
        # push the lambda 'event' onto the kinesis stream
        output = kinesis.put_record(
            StreamName=stream_name,
            Data=base64.b64encode(json.dumps(event)),
            PartitionKey=u'1'
        )
        logger.debug("Kinesis put_record response: {}".format(output))
        response = {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': 'Successfully forwarded webhook to Kinesis'
        }
    except Exception as e:
        logger.error(e.message)
        response = {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body':
                'Unable to forward the webhook. Error: {}'.format(e.message)
        }
    return response
