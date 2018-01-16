"""
This script is to be run inside a Jenkins job after updating bokchoy
db cache files through paver commands on edx-platform. If changes have
been made, this script will generate a PR into master with the updates.
"""
import sys
import logging
import os

import click
from github import Github
from git import Git

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
    'bok_choy_schema_student_module_history.sql'
]
BOKCHOY_DB_FILES.append(FINGERPRINT_FILE)


def _get_github_token():
    """
    Get the github token environment variable.
    """
    try:
        github_token = os.environ.get('GITHUB_TOKEN')
    except:
        raise StandardError(
            "Could not find env variable GITHUB_TOKEN. "
            "Please make sure the variable is set and try again."
        )
    return github_token


def _authenticate_with_github():
    """
    Authenticate with Github using a token and return the instance.
    """
    github_token = _get_github_token()
    try:
        github_instance = Github(github_token)
    except:
        raise StandardError(
            "Failed connecting to Github. " +
            "Please make sure the github token is accurate and try again."
        )
    return github_instance


def _connect_to_repo(repo_name):
    """
    Get the repository object of the desired repo.
    """
    github_instance = _authenticate_with_github()
    repos_list = github_instance.get_user().get_repos()
    repository = None
    for repo in repos_list:
        if repo.name == repo_name:
            return repo

    raise StandardError(
        "Could not connect to the repository: {}. "
        "Please make sure you are using the correct "
        "credentials and try again.".format(repo_name)
    )


def _read_local_file_contents(repo_root, db_file):
    """
    Read the contents of a file and return a string of the data.
    """
    file_path = os.path.join(repo_root, DB_CACHE_FILEPATH, db_file)
    try:
        with open(file_path, 'r') as opened_file:
            data = opened_file.read()
    except:
        raise StandardError(
            "Unable to read file: {}".format(file_path)
        )
    return data


def _branch_exists(repository, branch_name):
    """
    Checks to see if this branch name already exists
    """
    try:
        repository.get_branch(branch_name)
    except:
        return False
    return True


def _get_file_sha(repository, file_path):
    """
    Finds the sha of a specific file on master.
    Returns the file sha, or None if the file doesn't exist.
    """
    try:
        # Get the blob sha of the db file on our branch
        file_sha = repository.get_file_contents(file_path).sha
    except:
        logger.info("Could not locate file: {}".format(file_path))
        file_sha = None
    return file_sha


def _get_git_instance(repo_root):
    """
    Gets the git instance of the edx-platform repository.
    """
    git_instance = Git(repo_root)
    git_instance.init()
    return git_instance


def _get_modified_files_list(repo_root):
    """
    Use the Git library to run the ls-files command to find
    the list of files modified.
    """
    git_instance = _get_git_instance(repo_root)
    return git_instance.ls_files("-m")


def _file_has_changed(db_file, modified_files):
    """
    Determine if the db file is among the changed files.
    """
    file_path = os.path.join(DB_CACHE_FILEPATH, db_file)
    return file_path in modified_files


def _create_branch(repository, branch_name, sha):
    """
    Create a new branch with the given sha as its head.
    """
    try:
        branch_object = repository.create_git_ref(branch_name, sha)
    except:
        raise StandardError(
            "Unable to create git branch: {}. "
            "Check to make sure this branch doesn't already exist.".format(branch_name)
        )
    return branch_object


def _update_file(repository, file_path, commit_message, contents, file_sha, branch_name):
    """
    Create a commit on a branch that updates the file_path with the string contents.
    """
    try:
        repository.update_file(file_path, commit_message, contents, file_sha, branch_name)
    except:
        raise StandardError(
            "Error updating database file: {}".format(file_path)
        )


def _create_file(repository, file_path, commit_message, contents, branch_name):
    """
    Create a commit on a branch that creates a new file with the string contents.
    """
    try:
        repository.create_file(file_path, commit_message, contents, branch_name)
    except:
        raise StandardError(
            "Error creating database file: {}".format(file_path)
        )


def _create_pull_request(repository, title, body, base, head):
    """
    Create a new pull request with the changes in head.
    """
    try:
        pull_request = repository.create_pull(
            title=title,
            body=body,
            base=base,
            head=head
        )
    except:
        raise StandardError(
            "Could not create pull request"
        )


def _delete_branch(branch_object):
    """
    Delete a branch from a repository.
    """
    try:
        branch_object.delete()
    except:
        raise StandardError(
            "Failed to delete branch"
        )


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
    repository = _connect_to_repo("edx-platform")

    fingerprint = _read_local_file_contents(repo_root, FINGERPRINT_FILE)
    branch_name = "refs/heads/testeng/bokchoy_auto_cache_update_{}".format(fingerprint)

    if _branch_exists(repository, branch_name):
        # If this branch already exists, then there's already a PR
        # for this fingerprint. To avoid excessive PR's, exit.
        logger.info("Branch name: {} already exists. Exiting.".format(branch_name))
        return

    branch_object = _create_branch(repository, branch_name, sha)
    modified_files = _get_modified_files_list(repo_root)

    changes_made = False
    for db_file in BOKCHOY_DB_FILES:
        repo_file_path = os.path.join('/', DB_CACHE_FILEPATH, db_file)
        file_sha = _get_file_sha(repository, repo_file_path)
        if file_sha:
            if _file_has_changed(db_file, modified_files):
                logger.info("File {} has changed.".format(repo_file_path))
                local_file_data = _read_local_file_contents(repo_root, db_file)
                logger.info("Updating database file: {}".format(repo_file_path))
                _update_file(repository, repo_file_path, 'Updating migrations', local_file_data, file_sha, branch_name)
                changes_made = True
        else:
            logger.info("Creating new database file: {}".format(repo_file_path))
            local_file_data = _read_local_file_contents(repo_root, db_file)
            _create_file(repository, repo_file_path, 'Updating', local_file_data, branch_name)
            changes_made = True

    if changes_made:
        logger.info("Creating a new pull request.")
        _create_pull_request(
            repository,
            'Bokchoy db cache update',
            '@edx/testeng please review',
            'master',
            branch_name
        )
    else:
        logger.info("No changes needed. Deleting branch: {}".format(branch_name))
        _delete_branch(branch_object)


if __name__ == "__main__":
    main()
