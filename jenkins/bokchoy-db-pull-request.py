import sys
import logging
import os
import click
from github import Github

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

DB_CACHE_FILEPATH = 'common/test/db_cache/'

BOKCHOY_DB_FILES = [
    'bok_choy_data_default.json',
    'bok_choy_data_student_module_history.json',
    'bok_choy_migrations_data_default.sql',
    'bok_choy_migrations_data_student_module_history.sql',
    'bok_choy_schema_default.sql',
    'bok_choy_schema_student_module_history.sql',
    # 'bok_choy_default_migrations.yaml',
    # 'bok_choy_student_module_history_migrations.yaml'
]


@click.command()
@click.option(
    '--sha',
    help="Sha of the merge commit to base the new PR off of.",
    required=True,
)
@click.option(
    '--github_token',
    help="Github token for authentication",
    required=True,
)
@click.option(
    '--repo_root',
    help="Path to local edx-platform repository that will "
         "hold updated database files.",
    required=True,
)
def main(sha, github_token, repo_root):
    # Connect to Github
    try:
        logger.info("Authenticating with Github.")
        github_instance = Github(github_token)
    except:
        logger.error(
            "Failed connecting to Github. " +
            "Please make sure the credentials are accurate and try again."
        )
        sys.exit(1)

    # Connect to the edx-platform repo
    repos_list = github_instance.get_user().get_repos()
    repository = None
    for repo in repos_list:
        if repo.name == 'edx-platform':
            repository = repo
            break
    if not repository:
        logger.error("Could not connect to the repository: edx-platform")
        sys.exit(1)

    # Create a new branch for the db file changes
    branch_name = "refs/heads/bokchoy_auto_cache_update_" + sha
    try:
        logger.info("Creating git branch: {}".format(branch_name))
        ref = repository.create_git_ref(branch_name, sha)
    except:
        logger.error("Unable to create git branch: {}".format(branch_name))
        sys.exit(1)

    # Iterate through the db files and update them accordingly
    for db_file in BOKCHOY_DB_FILES:
        # Create the path to the db file
        file_path = os.path.join(DB_CACHE_FILEPATH, db_file)
        # The pygithub library needs a forward slash in front of file paths
        forward_slash_path = os.path.join('/', file_path)
        try:
            # Get the blob sha of the db file on our branch
            file_sha = repository.get_file_contents(forward_slash_path).sha
        except:
            logger.error("Could not locate file: {}".format(forward_slash_path))
            sys.exit(1)

        # Read the local db files that were updated by paver
        local_file_path = os.path.join(repo_root, file_path)
        with open(local_file_path, 'r') as local_db_file:
            new_file = local_db_file.read()

        # Update the db files on our branch to reflect the new changes
        logger.info("Updating database file: {}".format(file_path))
        try:
            repository.update_file(forward_slash_path, 'Updating migrations', new_file, file_sha, branch_name)
        except:
            logger.error("Error updating database file: {}".format(file_path))
            sys.exit(1)

    # Create a pull request against master and tag testeng for further action
    try:
        logger.info("Creating pull request with comment tag to @edx/testeng")
        pull_request = repository.create_pull(
            title='Bokchoy db cache update',
            body='@michaelyoungstrom please review',
            base='master',
            head=branch_name
        )
    except:
        logger.error("Error creating pull request")
        sys.exit(1)


if __name__ == "__main__":
    main()
