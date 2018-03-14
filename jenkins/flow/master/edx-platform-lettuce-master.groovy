import hudson.FilePath
import hudson.model.*

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("GIT_COMMIT")
def jenkinsUrl = build.environment.get("JENKINS_URL")
def jobUrl = jenkinsUrl + build.url
def subsetJob = build.environment.get("SUBSET_JOB") ?: "edx-platform-test-subset"
def repoName = build.environment.get("REPO_NAME") ?: "edx-platform"
def workerLabel = build.environment.get("WORKER_LABEL") ?: "jenkins-worker"

try{
  def statusJobParams = [
    new StringParameterValue("GITHUB_ORG", "edx"),
    new StringParameterValue("GITHUB_REPO", repoName),
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
          lettuce_lms = build(subsetJob, sha1: sha1, SHARD: "all", TEST_SUITE: "lms-acceptance", PARENT_BUILD: "master #" + build.number, WORKER_LABEL: workerLabel)
          toolbox.slurpArtifacts(lettuce_lms)
        },
        {
          lettuce_cms = build(subsetJob, sha1: sha1, SHARD: "all", TEST_SUITE: "cms-acceptance", PARENT_BUILD: "master #" + build.number, WORKER_LABEL: workerLabel)
          toolbox.slurpArtifacts(lettuce_cms)
        },
    )
  }rescue{
    FilePath artifactsDir =  new FilePath(build.artifactManager.getArtifactsDir())
    artifactsDir.copyRecursiveTo(build.workspace)

    // Delete the report artifacts that we copied from the subset job up into
    // the staging area, to reduce disk usage and network i/o.
    List toDelete = artifactsDir.list().findAll { item ->
        item.getName() != 'test_root'
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
