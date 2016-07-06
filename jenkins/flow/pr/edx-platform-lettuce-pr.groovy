import hudson.FilePath
import hudson.model.*

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("ghprbActualCommit")
def job = build.environment.get("JOB_NAME")

if (job.contains("private")) {
    subsetJob = "edx-platform-test-subset_private"
    platformName = "edx-platform-private"
}
else {
    subsetJob = "edx-platform-test-subset"
    platformName = "edx-platform"
}

guard{
  parallel(
    {
      lettuce_lms = build(subsetJob, sha1: sha1, SHARD: "all", TEST_SUITE: "lms-acceptance", PARENT_BUILD: "PR Build #" + build.number)
      toolbox.slurpArtifacts(lettuce_lms)
    },
    {
      lettuce_cms = build(subsetJob, sha1: sha1, SHARD: "all", TEST_SUITE: "cms-acceptance", PARENT_BUILD: "PR Build #" + build.number)
      toolbox.slurpArtifacts(lettuce_cms)
    },
  )
}rescue{
  FilePath artifactsDir =  new FilePath(build.artifactManager.getArtifactsDir())
  FilePath copyToDir = new FilePath(build.workspace, platformName)
  artifactsDir.copyRecursiveTo(copyToDir)
}
