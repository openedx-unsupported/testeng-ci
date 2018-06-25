import argparse
import boto3
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JenkinsContainerManager():
    """
    Responsible for spinning up and terminating jenkins-worker containers
    on build jenkins.
    """

    def __init__(self, region, cluster):
        self.ecs = boto3.client('ecs', region)
        self.cluster_name = cluster

    def spin_up_containers(self, number_of_containers, task_name, subnets, security_groups, public_ip_enabled, launch_type):
        """
        Spins up jenkins-worker containers. The run_task boto3 command can only run 10 tasks
        at a time, so this method runs it multiple times if needed.
        """
        revision = self.ecs.describe_task_definition(taskDefinition=task_name)['taskDefinition']['revision']
        task_definition = task_name + ":{}".format(revision)

        logging.info("Spinning up {} containers based on task definition: {}".format(number_of_containers, task_definition))

        remainder = number_of_containers % 10
        dividend = number_of_containers / 10

        container_num_list = [10 for i in range(0, dividend)]
        if remainder:
            container_num_list.append(remainder)

        task_arns = []
        for num in container_num_list:
            response = self.ecs.run_task(
                count = num,
                cluster = self.cluster_name,
                launchType = launch_type,
                networkConfiguration = {
                    'awsvpcConfiguration': {
                        'subnets': subnets,
                        'securityGroups': security_groups,
                        'assignPublicIp': public_ip_enabled
                    }
                },
                taskDefinition = task_definition
            )

            for task_response in response['tasks']:
                task_arns.append(task_response['taskArn'])

        still_running = task_arns; not_running = []; all_running = False
        for attempt in range(0, 10):
            time.sleep(60)
            list_tasks_response = self.ecs.describe_tasks(cluster=self.cluster_name, tasks=still_running)['tasks']
            del not_running[:]
            for counter, task_response in enumerate(list_tasks_response):
                if task_response['lastStatus'] != 'RUNNING':
                    not_running.append(task_response['taskArn'])

            if not_running:
                logger.info("Still waiting on {} containers to spin up".format(len(not_running)))
            else:
                logger.info("Finished spinning up containers")
                all_running = True
                break

        if not all_running:
            raise StandardError(
                "Timed out waiting to spin up all containers."
            )


    def terminate_containers(self, task_arns, reason):
        """
        Terminates jenkins-worker containers.
        """
        for task_arn in task_arns:
            response = self.ecs.stop_task(
                cluster = self.cluster_name,
                task = task_arn,
                reason = reason
            )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="JenkinsContainerManager, manages ECS containers in an AWS cluster."
    )

    parser.add_argument('--region', '-g', default='us-east-1',
                        help="AWS region where ECS infrastructure lives")

    parser.add_argument('--cluster', '-c', default='jenkins-worker-containers',
                        help="AWS Cluster name where the containers live")

    parser.add_argument('--action', '-a', choices=['spin_up', 'terminate'], default=None,
                        help="Action for JenkinsContainerManager to perform. "
                        "Either spinning up or terminating AWS ECS workers")

    # Spinning up containers
    parser.add_argument('--num_containers', '-n', type=int, default=1,
                        help="Number of containers to spin up")

    parser.add_argument('--task_name', '-t', default=None,
                        help="Name of the task definition for spinning up workers")

    parser.add_argument('--subnets', '-s', action='append', default=None,
                        help="List of subnets for the containers to exist in")

    parser.add_argument('--security_groups', '-sg', action='append', default=None,
                        help="List of security groups to apply to the containers")

    parser.add_argument('--public_ip_enabled', choices=['ENABLED', 'DISABLED'],
                        default='DISABLED', help="Whether the containers should have a public IP")

    parser.add_argument('--launch_type', default='FARGATE', choices=['EC2', 'FARGATE'],
                        help="ECS launch type of container.")

    # Terminating containers
    parser.add_argument('--task_arns', '-arns', action='append', default=None,
                        help="Task arns to terminate")

    parser.add_argument('--reason', '-r', default="",
                        help="Reason for terminating containers")

    args = parser.parse_args()
    containerManager = JenkinsContainerManager(args.region, args.cluster)

    if args.action == 'spin_up':
        containerManager.spin_up_containers(
            args.num_containers,
            args.task_name,
            args.subnets,
            args.security_groups,
            args.public_ip_enabled,
            args.launch_type
        )
    elif args.action == 'terminate':
        containerManager.terminate_containers(
            args.task_arns,
            args.reason
        )
