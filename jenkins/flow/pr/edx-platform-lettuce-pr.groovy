import hudson.FilePath
import hudson.model.*

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("ghprbActualCommit")
def subsetJob = build.environment.get("SUBSET_JOB") ?: "edx-platform-test-subset"
def workerLabel = build.environment.get("WORKER_LABEL") ?: "jenkins-worker"

guard{
  parallel(
    {
      lettuce_lms = build(subsetJob, sha1: sha1, SHARD: "all", TEST_SUITE: "lms-acceptance", PARENT_BUILD: "PR Build #" + build.number, WORKER_LABEL: workerLabel)
      toolbox.slurpArtifacts(lettuce_lms)
    },
    {
      lettuce_cms = build(subsetJob, sha1: sha1, SHARD: "all", TEST_SUITE: "cms-acceptance", PARENT_BUILD: "PR Build #" + build.number, WORKER_LABEL: workerLabel)
      toolbox.slurpArtifacts(lettuce_cms)
    },
  )
}rescue{
  FilePath artifactsDir =  new FilePath(build.artifactManager.getArtifactsDir())
  artifactsDir.copyRecursiveTo(build.workspace)
}
