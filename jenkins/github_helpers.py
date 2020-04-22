"""
Helper methods for connecting with Github
"""
from __future__ import absolute_import
import io
import logging
import os

from git import Git
from github import Github, GithubObject, InputGitAuthor, InputGitTreeElement

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_github_token():
    """
    Get the github token environment variable.
    """
    try:
        github_token = os.environ.get('GITHUB_TOKEN')
    except:
        raise Exception(
            "Could not find env variable GITHUB_TOKEN. "
            "Please make sure the variable is set and try again."
        )
    return github_token


def get_user_email():
    """
    Get the github user email environment variable.
    """
    try:
        github_user_email = os.environ.get('GITHUB_USER_EMAIL')
    except:
        raise Exception(
            "Could not find env variable GITHUB_USER_EMAIL. "
            "Please make sure the variable is set and try again."
        )
    return github_user_email


def authenticate_with_github():
    """
    Authenticate with Github using a token and return the instance.
    """
    github_token = get_github_token()
    try:
        github_instance = Github(github_token)
    except:
        raise Exception(
            "Failed connecting to Github. " +
            "Please make sure the github token is accurate and try again."
        )
    return github_instance


def connect_to_repo(github_instance, repo_name):
    """
    Get the repository object of the desired repo.
    """
    repos_list = github_instance.get_user().get_repos()
    for repo in repos_list:
        if repo.name == repo_name:
            return repo

    raise Exception(
        "Could not connect to the repository: {}. "
        "Please make sure you are using the correct "
        "credentials and try again.".format(repo_name)
    )


def branch_exists(repository, branch_name):
    """
    Checks to see if this branch name already exists
    """
    try:
        repository.get_branch(branch_name)
    except:
        return False
    return True


def get_modified_files_list(repo_root):
    """
    Use the Git library to run the ls-files command to find
    the list of files modified.
    """
    git_instance = Git(repo_root)
    git_instance.init()
    modified_files = git_instance.ls_files("--modified")
    if len(modified_files) > 0:
        return modified_files.split("\n")
    else:
        return []


def create_branch(repository, branch_name, sha):
    """
    Create a new branch with the given sha as its head.
    """
    try:
        branch_object = repository.create_git_ref(branch_name, sha)
    except:
        raise Exception(
            "Unable to create git branch: {}. "
            "Check to make sure this branch doesn't already exist.".format(branch_name)
        )
    return branch_object


def close_existing_pull_requests(repository, user_login, user_name):
    """
    Close any existing PR's by the bot user in this PR. This will help
    reduce clutter, since any old PR's will be obsolete.
    """
    pulls = repository.get_pulls(state="open")
    deleted_pull_numbers = []
    for pr in pulls:
        user = pr.user
        if user.login == user_login and user.name == user_name:
            logger.info("Deleting PR: #{}".format(pr.number))
            pr.create_issue_comment("Closing obsolete PR.")
            pr.edit(state="closed")
            deleted_pull_numbers.append(pr.number)

            branch_name = pr.head.ref
            delete_branch(repository, branch_name)
    return deleted_pull_numbers


def create_pull_request(repository, title, body, base, head, user_reviewers=GithubObject.NotSet,
                        team_reviewers=GithubObject.NotSet):
    """
    Create a new pull request with the changes in head. And tag a list of teams
    for a review.
    """
    try:
        pull_request = repository.create_pull(
            title=title,
            body=body,
            base=base,
            head=head
        )
        pull_request.create_review_request(reviewers=user_reviewers, team_reviewers=team_reviewers)
    except:
        raise Exception(
            "Could not create pull request"
        )


def delete_branch(repository, branch_name):
    """
    Delete a branch from a repository.
    """
    logger.info("Deleting Branch: {}".format(branch_name))
    try:
        ref = "heads/{}".format(branch_name)
        branch_object = repository.get_git_ref(ref)
        branch_object.delete()
    except:
        raise Exception(
            "Failed to delete branch"
        )


def get_file_contents(repo_root, file_path):
    """
    Return contents of local file
    """
    try:
        full_file_path = os.path.join(repo_root, file_path)
        with io.open(full_file_path, 'r') as opened_file:
            data = opened_file.read()
    except:
        raise Exception(
            "Unable to read file: {}".format(file_path)
        )
    return data


def update_list_of_files(repository, repo_root, file_path_list, commit_message, sha, username):
    input_trees_list = []
    base_git_tree = repository.get_git_tree(sha)
    for file_path in file_path_list:
        content = get_file_contents(repo_root, file_path)
        input_tree = InputGitTreeElement(file_path, "100644", "blob", content=content)
        input_trees_list.append(input_tree)
    if len(input_trees_list) > 0:
        new_git_tree = repository.create_git_tree(input_trees_list, base_tree=base_git_tree)
        parents = [repository.get_git_commit(sha)]
        author = InputGitAuthor(username, get_user_email())
        commit_sha = repository.create_git_commit(
            commit_message, new_git_tree, parents, author=author, committer=author
        ).sha
        return commit_sha
