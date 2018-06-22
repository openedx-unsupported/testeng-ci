import boto3

# Param Definitions:
COUNT = 1 # Number of Tasks to spin up.. up to 10 in one call
CLUSTER = 'jenkins-worker-containers' # Name of our cluster to run the containers in
PUBLIC_IP_CHOICE = 'DISABLED' # Whether we want the container to have a public IP 'ENABLED' | 'DISABLED'
SECURITY_GROUPS = [ 'sg-7ad8810f' ] # List of Security Groups for our container
SUBNETS = [ 'subnet-40feb509' ] # List of Subnets for our container
TASK_NAME = 'jenkins-worker-container' # Name of our Task Definition

ecs_client = boto3.client('ecs', 'us-east-1')

revision = ecs_client.describe_task_definition(taskDefinition=TASK_NAME)['taskDefinition']['revision']
task_definition = TASK_NAME + ":{}".format(revision)

networkConfiguration = {
    'awsvpcConfiguration': {
        'subnets': SUBNETS,
        'securityGroups': SECURITY_GROUPS,
        'assignPublicIp': PUBLIC_IP_CHOICE
    }
}

response = ecs_client.run_task(
    count=COUNT,
    cluster=CLUSTER,
    launchType='FARGATE',
    networkConfiguration=networkConfiguration,
    taskDefinition=task_definition
)
