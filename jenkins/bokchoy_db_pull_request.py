"""
This script is to be run inside a Jenkins job after updating bokchoy
db cache files through paver commands on edx-platform. If changes have
been made, this script will generate a PR into master with the updates.
"""
from __future__ import absolute_import

import logging
import os

import click

from .github_helpers import GitHubHelper

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

DB_CACHE_FILEPATH = 'common/test/db_cache'

FINGERPRINT_FILE = 'bok_choy_migrations.sha1'
BOKCHOY_DB_FILES = [
    'bok_choy_data_default.json',
    'bok_choy_data_student_module_history.json',
    'bok_choy_migrations_data_default.sql',
    'bok_choy_migrations_data_student_module_history.sql',
    'bok_choy_schema_default.sql',
    'bok_choy_schema_student_module_history.sql',
    FINGERPRINT_FILE
]

github_helper = GitHubHelper()


def _read_local_db_file_contents(repo_root, db_file):
    """
    Read the contents of a file and return a string of the data.
    """
    file_path = os.path.join(DB_CACHE_FILEPATH, db_file)
    return github_helper.get_file_contents(repo_root, file_path)


@click.command()
@click.option(
    '--sha',
    help="Sha of the merge commit to base the new PR off of",
    required=True,
)
@click.option(
    '--repo_root',
    help="Path to local edx-platform repository that will "
         "hold updated database files",
    required=True,
)
def main(sha, repo_root):
    logger.info("Authenticating with Github")
    github_instance = github_helper.get_github_instance()
    repository = github_helper.connect_to_repo(github_instance, "edx-platform")

    all_modified_files = github_helper.get_modified_files_list(repo_root)
    bokchoy_db_files_full_path = [os.path.join(DB_CACHE_FILEPATH, db_file) for db_file in BOKCHOY_DB_FILES]
    modified_files_list = [file for file in all_modified_files if file in bokchoy_db_files_full_path]
    logger.info("modified db files: {}".format(modified_files_list))
    if len(modified_files_list) > 0:
        fingerprint = _read_local_db_file_contents(repo_root, FINGERPRINT_FILE)
        branch = "refs/heads/testeng/bokchoy_auto_cache_update_{}".format(fingerprint)

        if github_helper.branch_exists(repository, branch):
            # If this branch already exists, then there's already a PR
            # for this fingerprint. To avoid excessive PR's, exit.
            logger.info("Branch name: {} already exists. Exiting.".format(branch))
        else:
            git_tree = repository.get_git_tree(sha)
            user = github_instance.get_user()
            commit_sha = github_helper.update_list_of_files(
                repository,
                repo_root,
                modified_files_list,
                "Updating Bokchoy testing database cache",
                sha,
                user.name
            )
            github_helper.create_branch(repository, branch, commit_sha)

            logger.info("Checking if there's any old pull requests to delete")
            deleted_pulls = github_helper.close_existing_pull_requests(repository, user.login, user.name)

            pr_body = "Bokchoy testing database update"
            for num, deleted_pull_number in enumerate(deleted_pulls):
                if num == 0:
                    pr_body += "\n\nDeleted obsolete pull_requests:"
                pr_body += "\nhttps://github.com/edx/edx-platform/pull/{}".format(deleted_pull_number)

            logger.info("Creating a new pull request")
            github_helper.create_pull_request(
                repository,
                'Bokchoy Testing DB Cache update',
                pr_body,
                'master',
                branch,
                team_reviewers=['arbi-bom']
            )
    else:
        logger.info("No changes needed")


if __name__ == "__main__":
    main()
