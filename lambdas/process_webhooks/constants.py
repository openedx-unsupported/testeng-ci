# Create constants that hold lists of jobs.
# These will be used when querying the Jenkins
# API to ensure all expected jobs have been triggered.
EDX_PLATFORM_CONTEXTS = [
    "-accessibility-",
    "-bok-choy-",
    "-js-",
    "-lettuce-",
    "-python-unittests-",
    "-quality-",
]

platform_jobs = [
    "EDX_PLATFORM_PR",
    "EDX_PLATFORM_FICUS_PR",
    "EDX_PLATFORM_GINKGO_PR",
    "EDX_PLATFORM_PRIVATE_PR",
]

platform_job_names_by_context = [
    [
        "edx-platform" + base + "pr",
        "eucalyptus" + base + "pr",
        "ficus" + base + "pr",
        "ginkgo" + base + "pr",
        "edx-platform" + base + "pr_private",
    ]
    for base in EDX_PLATFORM_CONTEXTS
]

platform_jobs_by_branch_type = list(zip(*platform_job_names_by_context))
JOBS_DICT = dict(zip(platform_jobs, platform_jobs_by_branch_type))

# OpenEdX release branch names
RELEASE_BRANCHES = {
    "refs/heads/open-release/eucalyptus.master": "eucalyptus",
    "refs/heads/open-release/ficus.master": "ficus",
    "refs/heads/open-release/ginkgo.master": "ginkgo"
}

CREDENTIALS_BUCKET = "edx-tools-credentials"
CREDENTIALS_FILE = "edx_tools_core_jenkins_credentials.json"
