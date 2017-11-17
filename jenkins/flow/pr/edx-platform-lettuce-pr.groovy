import hudson.FilePath
import hudson.model.*

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("ghprbActualCommit")
def subsetJob = build.environment.get("SUBSET_JOB") ?: "edx-platform-test-subset"
def repoName = build.environment.get("REPO_NAME") ?: "edx-platform"
def workerLabel = build.environment.get("WORKER_LABEL") ?: "jenkins-worker"
def djangoVersion = build.environment.get("DJANGO_VERSION") ?: " "

// Any environment variables that you want to inject into the environment of
// child jobs of this build flow should be added here (comma-separated,
// in the format VARIABLE=VALUE)
def envVarString = "DJANGO_VERSION=${djangoVersion}"

guard{
  parallel(
    {
      lettuce_lms = build(subsetJob,
                          sha1: sha1,
                          SHARD: "all",
                          TEST_SUITE: "lms-acceptance",
                          PARENT_BUILD: "PR Build #" + build.number,
                          WORKER_LABEL: workerLabel,
                          ENV_VARS: envVarString
                          )
      toolbox.slurpArtifacts(lettuce_lms)
    },
    {
      lettuce_cms = build(subsetJob,
                          sha1: sha1,
                          SHARD: "all",
                          TEST_SUITE: "cms-acceptance",
                          PARENT_BUILD: "PR Build #" + build.number,
                          WORKER_LABEL: workerLabel,
                          ENV_VARS: envVarString
                          )
      toolbox.slurpArtifacts(lettuce_cms)
    },
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
