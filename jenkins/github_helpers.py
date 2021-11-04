"""
Helper methods for connecting with Github
"""
import io  # pylint: disable=unused-import
import logging
import os
import re
import time

from git import Git, Repo
from github import Github, GithubObject, InputGitAuthor, InputGitTreeElement

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class GitHubHelper:  # pylint: disable=missing-class-docstring

    def __init__(self):
        self._set_github_token()
        self._set_user_email()
        self._set_github_instance()

    # FIXME: Does nothing, sets variable to None if env var missing
    def _set_github_token(self):
        try:
            self.github_token = os.environ.get('GITHUB_TOKEN')
        except Exception as error:
            raise Exception(
                "Could not find env variable GITHUB_TOKEN. "
                "Please make sure the variable is set and try again."
            ) from error

    # FIXME: Does nothing, sets variable to None if env var missing
    def _set_user_email(self):
        try:
            self.github_user_email = os.environ.get('GITHUB_USER_EMAIL')
        except Exception as error:
            raise Exception(
                "Could not find env variable GITHUB_USER_EMAIL. "
                "Please make sure the variable is set and try again."
            ) from error

    def _set_github_instance(self):
        try:
            self.github_instance = Github(self.github_token)
        except Exception as error:
            raise Exception(
                "Failed connecting to Github. " +
                "Please make sure the github token is accurate and try again."
            ) from error

    def get_github_instance(self):
        return self.github_instance

    def get_github_token(self):
        return self.github_token

    # FIXME: Probably can end up picking repo from wrong org if two
    # repos have the same name in different orgs.
    #
    # Use repo_from_remote instead, and delete this when no longer in use.
    def connect_to_repo(self, github_instance, repo_name):
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

    def repo_from_remote(self, repo_root, remote_name_allow_list=None):
        """
        Get the repository object for a repository with a Github remote.

        Optionally restrict the remotes under consideration by passing a list
        of names as``remote_name_allow_list``, e.g. ``['origin']``.
        """
        patterns = [
            r"git@github\.com:(?P<name>[^/?#]+/[^/?#]+?).git",
            # Non-greedy match for repo name so that optional .git on
            # end is not included in repo name match.
            r"https?://(www\.)?github\.com/(?P<name>[^/?#]+/[^/?#]+?)(/|\.git)?"
        ]
        for remote in Repo(repo_root).remotes:
            if remote_name_allow_list and remote.name not in remote_name_allow_list:
                continue
            for url in remote.urls:
                for pattern in patterns:
                    m = re.fullmatch(pattern, url)
                    if m:
                        fullname = m.group('name')
                        logger.info("Discovered repo %s in remotes", fullname)
                        return self.github_instance.get_repo(fullname)
        raise Exception("Could not find a Github URL among repo's remotes")

    def branch_exists(self, repository, branch_name):
        """
        Checks to see if this branch name already exists
        """
        try:
            repository.get_branch(branch_name)
        except:  # pylint: disable=bare-except
            return False
        return True

    def get_current_commit(self, repo_root):
        """
        Get current commit ID of repo at repo_root.
        """
        return Git(repo_root).rev_parse('HEAD')

    def get_updated_files_list(self, repo_root, untracked_files_required=False):
        """
        Use the Git library to run the ls-files command to find
        the list of files updated.
        """
        git_instance = Git(repo_root)
        git_instance.init()

        if untracked_files_required:
            modified_files = git_instance.ls_files("--modified")
            untracked_files = git_instance.ls_files("--others", "--exclude-from=.gitignore")
            updated_files = modified_files + '\n' + untracked_files \
                if (len(modified_files) > 0 and len(untracked_files) > 0) \
                else modified_files + untracked_files

        else:
            updated_files = git_instance.ls_files("--modified")

        if len(updated_files) > 0:
            return updated_files.split("\n")
        else:
            return []

    def create_branch(self, repository, branch_name, sha):
        """
        Create a new branch with the given sha as its head.
        """
        try:
            branch_object = repository.create_git_ref(branch_name, sha)
        except Exception as error:
            raise Exception(
                "Unable to create git branch: {}. "
                "Check to make sure this branch doesn't already exist.".format(branch_name)
            ) from error
        return branch_object

    def close_existing_pull_requests(self, repository, user_login, user_name, target_branch='master',
                                     branch_name_filter=None):
        """
        Close any existing PR's by the bot user in this PR. This will help
        reduce clutter, since any old PR's will be obsolete.
        If function branch_name_filter is specified, it will be called with
        branch names of PRs. The PR will only be closed when the function
        returns true.
        """
        pulls = repository.get_pulls(state="open")
        deleted_pull_numbers = []
        for pr in pulls:
            user = pr.user
            if user.login == user_login and user.name == user_name and pr.base.ref == target_branch:
                branch_name = pr.head.ref
                if branch_name_filter and not branch_name_filter(branch_name):
                    continue
                logger.info("Deleting PR: #{}".format(pr.number))
                pr.create_issue_comment("Closing obsolete PR.")
                pr.edit(state="closed")
                deleted_pull_numbers.append(pr.number)

                self.delete_branch(repository, branch_name)
        return deleted_pull_numbers

    def create_pull_request(self, repository, title, body, base, head, user_reviewers=GithubObject.NotSet,
                            team_reviewers=GithubObject.NotSet, verify_reviewers=True, draft=False):
        """
        Create a new pull request with the changes in head. And tag a list of teams
        for a review.
        """
        try:
            pull_request = repository.create_pull(
                title=title,
                body=body,
                base=base,
                head=head,
                draft=draft
            )
        except Exception as e:
            raise Exception("Failed to create pull request") from e

        try:
            any_reviewers = (user_reviewers is not GithubObject.NotSet or team_reviewers is not GithubObject.NotSet)
            if any_reviewers:
                logger.info("Tagging reviewers: users=%s and teams=%s", user_reviewers, team_reviewers)
                pull_request.create_review_request(
                    reviewers=user_reviewers,
                    team_reviewers=team_reviewers,
                )
                if verify_reviewers:
                    # Sometimes GitHub can't find the pull request we just made.
                    # Try waiting a moment before asking about it.
                    time.sleep(5)
                    self.verify_reviewers_tagged(pull_request, user_reviewers, team_reviewers)

        except Exception as e:
            raise Exception(
                "Some reviewers could not be tagged on new PR "
                "https://github.com/{}/pull/{}".format(repository.full_name, pull_request.number)
            ) from e

        return pull_request

    def verify_reviewers_tagged(self, pull_request, requested_users, requested_teams):
        """
        Assert if the reviewers we requested were tagged on the PR for review.

        Considerations:

        - Teams cannot be tagged on a PR unless that team has explicit write
          access to the repo.
        - Github may have independently tagged additional users or teams
          based on a CODEOWNERS file.
        """
        tagged_for_review = pull_request.get_review_requests()

        tagged_users = [user.login for user in tagged_for_review[0]]
        if not (requested_users is GithubObject.NotSet or set(requested_users) <= set(tagged_users)):
            logger.info("User taggging failure: Requested %s, actually tagged %s", requested_users, tagged_users)
            raise Exception('Some of the requested reviewers were not tagged on PR for review')

        tagged_teams = [team.name for team in tagged_for_review[1]]
        if not (requested_teams is GithubObject.NotSet or set(requested_teams) <= set(tagged_teams)):
            logger.info("Team taggging failure: Requested %s, actually tagged %s", requested_teams, tagged_teams)
            raise Exception('Some of the requested teams were not tagged on PR for review')

    def delete_branch(self, repository, branch_name):
        """
        Delete a branch from a repository.
        """
        logger.info("Deleting Branch: {}".format(branch_name))
        try:
            ref = "heads/{}".format(branch_name)
            branch_object = repository.get_git_ref(ref)
            branch_object.delete()
        except Exception as error:
            raise Exception(
                "Failed to delete branch"
            ) from error

    def get_file_contents(self, repo_root, file_path):
        """
        Return contents of local file
        """
        try:
            full_file_path = os.path.join(repo_root, file_path)
            with open(full_file_path, 'r', encoding='utf-8') as opened_file:
                data = opened_file.read()
        except Exception as error:
            raise Exception(
                "Unable to read file: {}".format(file_path)
            ) from error

        return data

    # pylint: disable=missing-function-docstring
    def update_list_of_files(self, repository, repo_root, file_path_list, commit_message, sha, username):
        input_trees_list = []
        base_git_tree = repository.get_git_tree(sha)
        for file_path in file_path_list:
            content = self.get_file_contents(repo_root, file_path)
            input_tree = InputGitTreeElement(file_path, "100644", "blob", content=content)
            input_trees_list.append(input_tree)
        if len(input_trees_list) > 0:
            new_git_tree = repository.create_git_tree(input_trees_list, base_tree=base_git_tree)
            parents = [repository.get_git_commit(sha)]
            author = InputGitAuthor(username, self.github_user_email)
            commit_sha = repository.create_git_commit(
                commit_message, new_git_tree, parents, author=author, committer=author
            ).sha
            return commit_sha

        return None
