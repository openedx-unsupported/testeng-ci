# Create constants that hold lists of jobs. These will be used when querying the Jenkins
# API to ensure all expected jobs have been triggered.
EDX_PLATFORM_BASE_TESTS = [
    "-accessibility-",
    "-bok-choy-",
    "-js-",
    "-lettuce-",
    "-python-unittests-",
    "-quality-",
]

# edx-platform tests
EDX_PLATFORM_MASTER = ["edx-platform" + base + "master" for base in EDX_PLATFORM_BASE_TESTS]
EDX_PLATFORM_PR = ["edx-platform" + base + "pr" for base in EDX_PLATFORM_BASE_TESTS]

EDX_PLATFORM_EUCALYPTUS_MASTER = ["eucalyptus" + base + "master" for base in EDX_PLATFORM_BASE_TESTS]
EDX_PLATFORM_EUCALYPTUS_PR = ["eucalyptus" + base + "pr" for base in EDX_PLATFORM_BASE_TESTS]

EDX_PLATFORM_FICUS_MASTER = ["ficus" + base + "master" for base in EDX_PLATFORM_BASE_TESTS]
EDX_PLATFORM_FICUS_PR = ["ficus" + base + "pr" for base in EDX_PLATFORM_BASE_TESTS]

# edx-platform-private tests
EDX_PLATFORM_PRIVATE_MASTER = ["edx-platform" + base + "master_private" for base in EDX_PLATFORM_BASE_TESTS]
EDX_PLATFORM_PRIVATE_PR = ["edx-platform" + base + "pr_private" for base in EDX_PLATFORM_BASE_TESTS]

# edx-e2e-tests
EDX_E2E_PR = [
    "microsites-staging-tests-pr",
    "edx-e2e-tests-pr"
]

# Create dictionary to find the proper credentials file name in S3 based on the Jenkins url.
# These files must exist in the S3 bucket specified in the webhook-processor environment variable.
JENKINS_S3_OBJECTS = {
    "https://build.testeng.edx.org": "build_jenkins_credentials",
    "https://test-jenkins.testeng.edx.org": "test_jenkins_credentials"
}
