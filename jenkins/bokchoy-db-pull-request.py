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
@click.option(
    '--repo_root',
    help="Path to local edx-platform repository that will "
         "hold updated database files.",
    required=True,
)
def main(sha, github_token, repo_root):
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
    changes_needed = False
    for db_file in db_files_list:
        try:
            # Get the blob sha of the file
            file_sha = repository.get_file_contents(db_file).sha
        except:
            logger.error("Could not locate file: {}".format(db_file))
            sys.exit(1)

        with open(db_file, 'r') as opened_db_file:
            current_file = opened_file.read()

        # Open the local db file and read to a String
        local_file_path = repo_root + db_file
        with open(local_file_path, 'r') as opened_local_file:
            new_file = opened_file.read()

        if current_file == new_file:
            logger.info('No differences needed for the db file: {}'.format(db_file))
        else:
            # Update the database file with the new changes
            changes_needed = True
            logger.info("Updating database file: {}".format(db_file))
            try:
                repository.update_file(db_file, 'Updating migrations', new_file, file_sha, branch_name)
            except:
                logger.error("Error updating database file: {}".format(db_file))
                sys.exit(1)

    # Create a pull request against master
    if changes_needed:
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
    else:
        logger.info('No changes to db cache needed for this merge.')


if __name__ == "__main__":
    main()
