import hudson.FilePath
import hudson.model.*

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("ghprbActualCommit")
def branch = build.environment.get("ghprbSourceBranch")
def subsetJob = build.environment.get("SUBSET_JOB") ?: "edx-platform-test-subset"
def repoName = build.environment.get("REPO_NAME") ?: "edx-platform"
def qualityDiffJob = build.environment.get("QUALITY_DIFF_JOB") ?: "edx-platform-quality-diff"
def workerLabel = build.environment.get("WORKER_LABEL") ?: "jenkins-worker"
def targetBranch = build.environment.get("TARGET_BRANCH") ?: "origin/master"

// Temporary fix until all edx-platform pull requests have rebased from master
// to get the fix in https://github.com/edx/edx-platform/pull/17252
FilePath thresholdFilePath = new FilePath(build.workspace, 'scripts/thresholds.sh')
File thresholdFile = new File(thresholdFilePath)
if(!thresholdFile.exists()) {
    String failMsg = 'The quality job has been refactored and requires a fix ' +
                     'in the platform. Please rebase your pr and rerun this test'
    throw new Exception("Build aborted: ${failMsg}")
}

guard{
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
