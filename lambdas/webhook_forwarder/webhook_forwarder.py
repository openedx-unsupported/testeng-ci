import json
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
            Data=json.dumps(event),
            PartitionKey=u'1'
        )
        logger.debug("Kinesis put_record response: {}".format(output))
        return output

    except Exception as e:
        logger.error(e.message)
        output = 'Unable to forward the webhook. Error: {}'.format(e.message)
        raise StandardError(output)
