import hudson.FilePath
import hudson.model.*

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("ghprbActualCommit")
def branch = build.environment.get("ghprbSourceBranch")
def subsetJob = build.environment.get("SUBSET_JOB") ?: "edx-platform-test-subset"
def qualityDiffJob = build.environment.get("QUALITY_DIFF_JOB") ?: "edx-platform-quality-diff"
def workerLabel = build.environment.get("WORKER_LABEL") ?: "jenkins-worker"
def targetBranch = build.environment.get("TARGET_BRANCH") ?: "origin/master"
def toxEnv = build.environment.get("TOX_ENV") ?: " "

// Any environment variables that you want to inject into the environment of
// child jobs of this build flow should be added here (comma-separated,
// in the format VARIABLE=VALUE)
def envVarString = "TOX_ENV=${toxEnv}"

guard{
    quality = parallel(
        {
            quality_job_1 = build(
                subsetJob,
                sha1: sha1,
                SHARD: "1",
                TEST_SUITE: "quality",
                PARENT_BUILD: "PR Build #" + build.number,
                WORKER_LABEL: workerLabel,
                ENV_VARS: envVarString
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
                WORKER_LABEL: workerLabel,
                ENV_VARS: envVarString
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
                WORKER_LABEL: workerLabel,
                ENV_VARS: envVarString
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
                WORKER_LABEL: workerLabel,
                ENV_VARS: envVarString
            )
            toolbox.slurpArtifacts(quality_job_4)
        },
    )
    quality_check = build(
        qualityDiffJob,
        QUALITY_BUILD_NUM_1: quality_job_1.number,
        QUALITY_BUILD_NUM_2: quality_job_2.number,
        QUALITY_BUILD_NUM_3: quality_job_3.number,
        QUALITY_BUILD_NUM_4: quality_job_4.number,
        sha1: sha1,
        PARENT_BUILD: "PR Build #" + build.number,
        CI_BRANCH: branch,
        TARGET_BRANCH: targetBranch
    )

    toolbox.slurpArtifacts(quality_check)
}rescue{
    FilePath artifactsDir =  new FilePath(build.artifactManager.getArtifactsDir())
    artifactsDir.copyRecursiveTo(build.workspace)

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
