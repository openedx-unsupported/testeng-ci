import hudson.FilePath
import hudson.model.*

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("ghprbActualCommit")

guard{
  parallel(
    {
      lettuce_lms = build('edx-platform-test-subset', sha1: sha1, SHARD: "all", TEST_SUITE: "lms-acceptance", PARENT_BUILD: "PR Build #" + build.number)
      toolbox.slurpArtifacts(lettuce_lms)
    },
    {
      lettuce_cms = build('edx-platform-test-subset', sha1: sha1, SHARD: "all", TEST_SUITE: "cms-acceptance", PARENT_BUILD: "PR Build #" + build.number)
      toolbox.slurpArtifacts(lettuce_cms)
    },
  )
}rescue{
  FilePath artifactsDir =  new FilePath(build.artifactManager.getArtifactsDir())
  artifactsDir.copyRecursiveTo(build.workspace)
}
