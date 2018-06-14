import hudson.FilePath
import hudson.model.*

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("ghprbActualCommit")
def subsetJob = build.environment.get("SUBSET_JOB") ?: "edx-platform-test-subset"
def workerLabel = build.environment.get("WORKER_LABEL") ?: "jenkins-worker"
def toxEnv = build.environment.get("TOX_ENV") ?: ""

// Any environment variables that you want to inject into the environment of
// child jobs of this build flow should be added here (comma-separated,
// in the format VARIABLE=VALUE)
def envVarString = "TOX_ENV=${toxEnv}"

guard{
    parallel(
      (1..22).collect { index ->
        return {
          bokchoybuild = build(subsetJob,
                               sha1: sha1,
                               SHARD: index,
                               TEST_SUITE: "bok-choy",
                               PARENT_BUILD: "master #" + build.number,
                               WORKER_LABEL: workerLabel,
                               ENV_VARS: envVarString
                               )
          toolbox.slurpArtifacts(bokchoybuild)

          }
        }
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
