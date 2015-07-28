import hudson.FilePath
import hudson.model.*

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("GIT_COMMIT")
def jenkinsUrl = build.environment.get("JENKINS_URL")
def jobUrl = jenkinsUrl + build.url


try{
  def statusJobParams = [
    new StringParameterValue("GITHUB_ORG", "edx"),
    new StringParameterValue("GITHUB_REPO", "edx-platform"),
    new StringParameterValue("GIT_SHA", "${sha1}"),
    new StringParameterValue("BUILD_STATUS", "pending"),
    new StringParameterValue("TARGET_URL", jobUrl),
    new StringParameterValue("DESCRIPTION", "Pending"),
    new StringParameterValue("CONTEXT", "jenkins/lettuce"),
  ]

  def statusJob = Hudson.instance.getJob('github-build-status')
  statusJob.scheduleBuild2(
      0,
      new Cause.UpstreamCause(build),
      new ParametersAction(statusJobParams)
  )

  println "Triggered github-build-status"
} finally{
  guard{
    parallel(
        {
          lettuce_lms = build('edx-platform-test-subset', sha1: sha1, SHARD: "all", TEST_SUITE: "lms-acceptance", PARENT_BUILD: "master #" + build.number)
          toolbox.slurpArtifacts(lettuce_lms)
        },
        {
          lettuce_cms = build('edx-platform-test-subset', sha1: sha1, SHARD: "all", TEST_SUITE: "cms-acceptance", PARENT_BUILD: "master #" + build.number)
          toolbox.slurpArtifacts(lettuce_cms)
        },
    )
  }rescue{
    FilePath artifactsDir =  new FilePath(build.artifactManager.getArtifactsDir())
    FilePath copyToDir = new FilePath(build.workspace, "edx-platform")
    artifactsDir.copyRecursiveTo(copyToDir)
  }
}
