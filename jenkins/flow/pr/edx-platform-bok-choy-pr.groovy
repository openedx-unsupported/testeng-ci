import hudson.FilePath
import hudson.model.*

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("ghprbActualCommit")
def subsetJob = build.environment.get("SUBSET_JOB") ?: "edx-platform-test-subset"
def repoName = build.environment.get("REPO_NAME") ?: "edx-platform"
def workerLabel = build.environment.get("WORKER_LABEL") ?: "jenkins-worker"

guard{
    parallel(
      (1..11).collect { index ->
        return {
          bokchoybuild = build(subsetJob, sha1: sha1, SHARD: index, TEST_SUITE: "bok-choy", PARENT_BUILD: "master #" + build.number, WORKER_LABEL: workerLabel)
          toolbox.slurpArtifacts(bokchoybuild)

          }
        }
    )
}rescue{
  FilePath artifactsDir =  new FilePath(build.artifactManager.getArtifactsDir())
  FilePath copyToDir = new FilePath(build.workspace, repoName)
  artifactsDir.copyRecursiveTo(copyToDir)
}
