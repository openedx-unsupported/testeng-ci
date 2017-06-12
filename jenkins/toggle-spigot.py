import boto3
import sys
import logging
import json
import click

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


@click.command()
@click.option(
    '--spigot_state',
    help="Set the state of the spigot lambda function. "
         "ON: The spigot will send webhooks directly "
         "to the target urls. "
         "OFF: The spigot will store webhooks in "
         "an SQS queue for future processing",
    required=True,
    type=click.Choice(['ON', 'OFF']),
)
def main(spigot_state):
    try:
        s3_client = boto3.client('s3')
    except:
        logger.error('Could not connect to s3')
        sys.exit(1)

    # Get the current state of the spigot
    current_state = _get_current_state(s3_client)

    if spigot_state == current_state:
        logger.info(
            'The spigot is already: {}'.format(current_state)
        )
    else:
        if spigot_state == 'ON':
            # Since the spigot is going from OFF to ON,
            # there may be webhooks in the SQS queue.
            # If so, drain these before turning the spigot ON.
            try:
                sqs_client = boto3.client('sqs')
                lambda_client = boto3.client('lambda')
            except:
                logger.error(
                    'Could not connect to sqs and/or lambda'
                )
                sys.exit(1)

            while _get_queue_size(sqs_client) > 0:
                # If there are messages in the queue,
                # invoke the lambda function
                _trigger_spigot_lambda(lambda_client)

            # The queue is empty
            logger.info(
                'The queue is fully drained.'
            )

        # Update s3 file to account for the new state
        _update_state(s3_client, spigot_state)
        logger.info(
            'The spigot is now: {}'.format(spigot_state)
        )


def _trigger_spigot_lambda(client):
    """
    Invoke the lambda function with an empty event.
    This will trigger the lambda to pop a message
    off the queue and send it to the desired endpoint(s).
    """
    try:
        response = client.invoke(
            FunctionName='spigot'
        )
    except:
        logger.error('Unable to invoke lambda function')
        sys.exit(1)


def _get_queue_size(client):
    """
    Get the size of the SQS queue.
    """
    try:
        queue_url_response = client.get_queue_url(
            QueueName='gh_webhooks_queue'
        )
        queue_url = queue_url_response['QueueUrl']
    except:
        logger.error('Unable to get queue url')
        sys.exit(1)

    try:
        response = client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['ApproximateNumberOfMessages']
        )
        # Convert to an integer, and return
        return int(response['Attributes']['ApproximateNumberOfMessages'])
    except:
        logger.error('Unable to get ApproximateNumberOfMessages from queue')
        sys.exit(1)


def _update_state(client, spigot_state):
    """
    Write the new state of the spigot to the S3 bucket.
    """
    spigot_state_dict = {'spigot_state': spigot_state}
    try:
        client.put_object(
            Bucket='edx-tools-spigot',
            Key='spigot_config.json',
            Body=json.dumps(spigot_state_dict)
        )
    except:
        logger.error('Unable to upload new spigot_state to S3')


def _get_current_state(client):
    """
    Get the current state of the spigot from
    the S3 bucket.
    """
    try:
        file = client.get_object(
            Bucket='edx-tools-spigot',
            Key='spigot_config.json'
        )
    except:
        raise StandardError(
            'Unable to get spigot_config.json file from S3'
        )

    body = json.loads(file['Body'].read())

    if not body.get("spigot_state"):
        raise StandardError(
            'Config file missing key: "spigot_state"'
        )

    return body["spigot_state"]


if __name__ == "__main__":
    main()
