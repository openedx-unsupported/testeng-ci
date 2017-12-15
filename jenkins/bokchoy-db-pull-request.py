import sys
import logging
import json
import click
from github import Github

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
def main(sha, github_token):
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

    # Create a new branch for the changes
    branch_name = "refs/heads/bokchoy_auto_cache_update_" + sha
    try:
        logger.info("Creating git branch: {}".format(branch_name))
        ref = repository.create_git_ref(branch_name, sha)
    except:
        logger.error("Unable to create git branch: {}".format(branch_name))
        sys.exit(1)

    db_files_list = [
        '/common/test/db_cache/bok_choy_data_default.json',
        '/common/test/db_cache/bok_choy_data_student_module_history.json',
        '/common/test/db_cache/bok_choy_migrations_data_default.sql',
        '/common/test/db_cache/bok_choy_migrations_data_student_module_history.sql',
        '/common/test/db_cache/bok_choy_schema_default.sql',
        '/common/test/db_cache/bok_choy_schema_student_module_history.sql',
        # '/common/test/db_cache/bok_choy_default_migrations.yaml',
        # '/common/test/db_cache/bok_choy_student_module_history_migrations.yaml'
    ]

    # Iterate through the db files and update them accordingly
    for db_file in db_files_list:
        try:
            # Get the blob sha of the file
            file_sha = repository.get_file_contents(db_file).sha
        except:
            logger.error("Could not locate file: {}".format(db_file))
            sys.exit(1)

        # Open the file and save it as a string
        with open('toggle-spigot.py', 'r') as opened_file:
            data = opened_file.read()

        # Update the database file with the new changes
        logger.info("Updating database file: {}".format(db_file))
        try:
            repository.update_file(db_file, 'Updating migrations', data, file_sha, branch_name)
        except:
            logger.error("Error updating database file: {}".format(db_file))
            sys.exit(1)

    # Create a pull request against master
    try:
        logger.info("Creating pull request with comment tag to @edx/testeng")
        pull_request = repository.create_pull(
            title='Bokchoy db cache update',
            body='@edx/testeng please review',
            base='master',
            head=branch_name
        )
    except:
        logger.error("Error creating pull request")
        sys.exit(1)


if __name__ == "__main__":
    main()
