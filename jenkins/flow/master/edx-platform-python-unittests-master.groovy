import hudson.FilePath
import hudson.model.*

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("GIT_COMMIT")
def jenkinsUrl = build.environment.get("JENKINS_URL")
def jobUrl = jenkinsUrl + build.url
def subsetJob = build.environment.get("SUBSET_JOB") ?: "edx-platform-test-subset"
def repoName = build.environment.get("REPO_NAME") ?: "edx-platform"
def coverageJob = build.environment.get("COVERAGE_JOB") ?: "edx-platform-unit-coverage"
def workerLabel = build.environment.get("WORKER_LABEL") ?: "jenkins-worker"
def targetBranch = build.environment.get("TARGET_BRANCH") ?: "origin/master"

try{
  def statusJobParams = [
    new StringParameterValue("GITHUB_ORG", "edx"),
    new StringParameterValue("GITHUB_REPO", repoName),
    new StringParameterValue("GIT_SHA", "${sha1}"),
    new StringParameterValue("BUILD_STATUS", "pending"),
    new StringParameterValue("TARGET_URL", jobUrl),
    new StringParameterValue("DESCRIPTION", "Pending"),
    new StringParameterValue("CONTEXT", "jenkins/python"),
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
    unit = parallel(
      {
        lms_unit_1 = build(subsetJob, sha1: sha1, SHARD: "1", TEST_SUITE: "lms-unit", PARENT_BUILD: "master #" + build.number, WORKER_LABEL: workerLabel)
        toolbox.slurpArtifacts(lms_unit_1)
      },
      {
        lms_unit_2 = build(subsetJob, sha1: sha1, SHARD: "2", TEST_SUITE: "lms-unit", PARENT_BUILD: "master #" + build.number, WORKER_LABEL: workerLabel)
        toolbox.slurpArtifacts(lms_unit_2)
      },
      {
        lms_unit_3 = build(subsetJob, sha1: sha1, SHARD: "3", TEST_SUITE: "lms-unit", PARENT_BUILD: "master #" + build.number, WORKER_LABEL: workerLabel)
        toolbox.slurpArtifacts(lms_unit_3)
      },
      {
        lms_unit_4 = build(subsetJob, sha1: sha1, SHARD: "4", TEST_SUITE: "lms-unit", PARENT_BUILD: "master #" + build.number, WORKER_LABEL: workerLabel)
        toolbox.slurpArtifacts(lms_unit_4)
      },
      {
        cms_unit = build(subsetJob, sha1: sha1, SHARD: "1", TEST_SUITE: "cms-unit", PARENT_BUILD: "master #" + build.number, WORKER_LABEL: workerLabel)
        toolbox.slurpArtifacts(cms_unit)
      },
      {
        commonlib_unit = build(subsetJob, sha1: sha1, SHARD: "1", TEST_SUITE: "commonlib-unit", PARENT_BUILD: "master #" + build.number, WORKER_LABEL: workerLabel)
        toolbox.slurpArtifacts(commonlib_unit)
      },
    )

    check_coverage = (
      lms_unit_1.result.toString() == 'SUCCESS' &&
      lms_unit_2.result.toString() == 'SUCCESS' &&
      lms_unit_3.result.toString() == 'SUCCESS' &&
      lms_unit_4.result.toString() == 'SUCCESS' &&
      cms_unit.result.toString() == 'SUCCESS' &&
      commonlib_unit.result.toString() == 'SUCCESS')

    if (check_coverage){
      unit_coverage = build(coverageJob,
                            UNIT_BUILD_NUM_1: commonlib_unit.number,
                            UNIT_BUILD_NUM_2: lms_unit_1.number,
                            UNIT_BUILD_NUM_3: lms_unit_2.number,
                            UNIT_BUILD_NUM_4: lms_unit_3.number,
                            UNIT_BUILD_NUM_5: lms_unit_4.number,
                            UNIT_BUILD_NUM_6: cms_unit.number,
                            sha1: sha1,
                            PARENT_BUILD: "master #" + build.number,
                            CI_BRANCH: "master",
                            TARGET_BRANCH: targetBranch
                           )

      toolbox.slurpArtifacts(unit_coverage)
    }
  }rescue{
    FilePath artifactsDir =  new FilePath(build.artifactManager.getArtifactsDir())
    FilePath copyToDir = new FilePath(build.workspace, repoName)
    artifactsDir.copyRecursiveTo(copyToDir)

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
