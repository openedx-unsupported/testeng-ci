"""
Exceptions used by the mobile app build scripts
"""

# Trigger Build


class MissingEnvironmentVariable(Exception):
    """
    Indicates that an expected environment variable was not found.
    """
    def __init__(self, variable):
        self.variable = variable
        super(MissingEnvironmentVariable, self).__init__()

    def __str__(self):
        return "Missing environment variable: {variable}".format(
            variable=self.variable
        )


class BranchAlreadyExists(Exception):
    """
    Indicates that the branch we're trying to create already exists
    """
    def __init__(self, branch_name):
        self.branch_name = branch_name
        super(BranchAlreadyExists, self).__init__()

    def __str__(self, branch_name):
        return "Branch already exists: {branch}".format(
            branch=branch_name
        )
