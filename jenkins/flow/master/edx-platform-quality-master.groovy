import hudson.FilePath
import hudson.model.*

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("GIT_COMMIT")
def jenkinsUrl = build.environment.get("JENKINS_URL")
def jobUrl = jenkinsUrl + build.url
def subsetJob = build.environment.get("SUBSET_JOB") ?: "edx-platform-test-subset"
def repoName = build.environment.get("REPO_NAME") ?: "edx-platform"
def workerLabel = build.environment.get("WORKER_LABEL") ?: "jenkins-worker"
def djangoVersion = build.environment.get("DJANGO_VERSION") ?: " "

// Any environment variables that you want to inject into the environment of
// child jobs of this build flow should be added here (comma-separated,
// in the format VARIABLE=VALUE)
def envVarString = "DJANGO_VERSION=${djangoVersion}"

try {
    def statusJobParams = [
        new StringParameterValue("GITHUB_ORG", "edx"),
        new StringParameterValue("GITHUB_REPO", repoName),
        new StringParameterValue("GIT_SHA", "${sha1}"),
        new StringParameterValue("BUILD_STATUS", "pending"),
        new StringParameterValue("TARGET_URL", jobUrl),
        new StringParameterValue("DESCRIPTION", "Pending"),
        new StringParameterValue("CONTEXT", "jenkins/quality"),
    ]

        def statusJob = Hudson.instance.getJob('github-build-status')
        if (params["SKIP_GITHUB_STATUS"] == null | params["SKIP_GITHUB_STATUS"] != "true") {
            statusJob.scheduleBuild2(
                0,
                new Cause.UpstreamCause(build),
                new ParametersAction(statusJobParams)
            )
            println "Triggered github-build-status"
        } else {
            println "Skipping github-build-status because SKIP_GITHUB_STATUS has been set"
        }
} finally {
    guard {
        quality = parallel(
            {
                quality_job_1 = build(
                    subsetJob,
                    sha1: sha1,
                    SHARD: "1",
                    TEST_SUITE: "quality",
                    PARENT_BUILD: "PR Build #" + build.number,
                    WORKER_LABEL: workerLabel
                )
                toolbox.slurpArtifacts(quality_job_1)
            },
            {
                quality_job_2 = build(
                    subsetJob,
                    sha1: sha1,
                    SHARD: "2",
                    TEST_SUITE: "quality",
                    PARENT_BUILD: "PR Build #" + build.number,
                    WORKER_LABEL: workerLabel
                )
                toolbox.slurpArtifacts(quality_job_2)
            },
            {
                quality_job_3 = build(
                    subsetJob,
                    sha1: sha1,
                    SHARD: "3",
                    TEST_SUITE: "quality",
                    PARENT_BUILD: "PR Build #" + build.number,
                    WORKER_LABEL: workerLabel
                )
                toolbox.slurpArtifacts(quality_job_3)
            },
            {
                quality_job_4 = build(
                    subsetJob,
                    sha1: sha1,
                    SHARD: "4",
                    TEST_SUITE: "quality",
                    PARENT_BUILD: "PR Build #" + build.number,
                    WORKER_LABEL: workerLabel
                )
                toolbox.slurpArtifacts(quality_job_4)
            },
        )
    } rescue{
        FilePath artifactsDir =  new FilePath(build.artifactManager.getArtifactsDir())
        FilePath copyToDir = new FilePath(build.workspace, repoName)
        artifactsDir.copyRecursiveTo(copyToDir)

        // Delete the report artifacts that we copied into the staging area,
        // to reduce disk usage.
        // Leave the 'test_root' directory, as it is indexed by Splunk for
        // paver timing reports.
        List toDelete = artifactsDir.list().findAll { item ->
            item.getName() != 'test_root' && item.getName() != 'reports'
        }
        toDelete.each { item ->
            if (item.isDirectory()) {
                item.deleteRecursive()
            } else {
                item.delete()
            }
        }
    }
}
