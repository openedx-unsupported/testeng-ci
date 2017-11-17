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
    new StringParameterValue("CONTEXT", "jenkins/bokchoy"),
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
} finally{
  guard{
    parallel(
      (1..11).collect { index ->
        return {
          bokchoybuild = build(subsetJob, sha1: sha1, SHARD: index, TEST_SUITE: "bok-choy", ENV_VARS: params["ENV_VARS"], PARENT_BUILD: "master #" + build.number, WORKER_LABEL: workerLabel)
          toolbox.slurpArtifacts(bokchoybuild)

          }
        }
    )
  }rescue{
    FilePath artifactsDir =  new FilePath(build.artifactManager.getArtifactsDir())
    FilePath copyToDir = new FilePath(build.workspace, repoName)
    try {
        artifactsDir.copyRecursiveTo(copyToDir)
    } catch (IOException e) {
        println("Couldn't copy artifacts into the workspace. Continuing")
    }
  }
}
