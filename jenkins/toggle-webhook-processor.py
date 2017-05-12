import boto3
import sys
import logging
import click

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


@click.command()
@click.option(
    '--enabled',
    help="Set the state of the trigger for the webhook-processor Lambda. "
         "True will enable the function to pull from the queue, "
         "False will disable it.",
    required=True,
    type=bool,
)
def main(enabled):
    try:
        # connect to aws lambda
        client = boto3.client('lambda')
    except Exception, e:
        # if connection failed, log error
        logger.error(e)
        sys.exit(1)

    try:
        # find event source mapping for webhook_processor
        response = client.list_event_source_mappings(
            FunctionName='webhook_processor'
        )
        uuid = response["EventSourceMappings"][0]["UUID"]
    except:
        # if none found, lambda does not exist
        logger.error(
            "No EventSourceMappings found for that lambda function name"
        )
        sys.exit(1)

    # call method according to the passed argument
    update_state(client, uuid, enabled)


def update_state(client, uuid, enabled):
    # find the previous state, update, and show new state
    previous_state = get_current_state(client, uuid)
    logger.info("The state was: " + previous_state)

    client.update_event_source_mapping(UUID=uuid, Enabled=enabled)
    current_state = get_current_state(client, uuid)
    logger.info("The state is now: " + current_state)


def get_current_state(client, uuid):
    # find the state by the lambda's uuid
    event = client.get_event_source_mapping(UUID=uuid)
    return event["State"]


if __name__ == "__main__":
    main()
