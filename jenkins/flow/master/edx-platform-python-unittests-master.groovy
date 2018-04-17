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
def djangoVersion = build.environment.get("DJANGO_VERSION") ?: " "
def targetBranch = build.environment.get("TARGET_BRANCH") ?: "origin/master"
def runCoverage = build.environment.get("RUN_COVERAGE") ?: "true"

// Any environment variables that you want to inject into the environment of
// child jobs of this build flow should be added here (comma-separated,
// in the format VARIABLE=VALUE)
def envVarString = "DJANGO_VERSION=${djangoVersion}, RUN_COVERAGE=${runCoverage}"

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
        lms_unit_1 = build(
          subsetJob,
          sha1: sha1,
          SHARD: "1",
          TEST_SUITE: "lms-unit",
          PARENT_BUILD: "master #" + build.number,
          WORKER_LABEL: workerLabel,
          ENV_VARS: envVarString
        )
        toolbox.slurpArtifacts(lms_unit_1)
      },
      {
        lms_unit_2 = build(
          subsetJob,
          sha1: sha1,
          SHARD: "2",
          TEST_SUITE: "lms-unit",
          PARENT_BUILD: "master #" + build.number,
          WORKER_LABEL: workerLabel,
          ENV_VARS: envVarString
        )
        toolbox.slurpArtifacts(lms_unit_2)
      },
      {
        lms_unit_3 = build(
          subsetJob,
          sha1: sha1,
          SHARD: "3",
          TEST_SUITE: "lms-unit",
          PARENT_BUILD: "master #" + build.number,
          WORKER_LABEL: workerLabel,
          ENV_VARS: envVarString
        )
        toolbox.slurpArtifacts(lms_unit_3)
      },
      {
        lms_unit_4 = build(
          subsetJob,
          sha1: sha1,
          SHARD: "4",
          TEST_SUITE: "lms-unit",
          PARENT_BUILD: "master #" + build.number,
          WORKER_LABEL: workerLabel,
          ENV_VARS: envVarString
        )
        toolbox.slurpArtifacts(lms_unit_4)
      },
      {
        lms_unit_5 = build(
          subsetJob,
          sha1: sha1,
          SHARD: "5",
          TEST_SUITE: "lms-unit",
          PARENT_BUILD: "master #" + build.number,
          WORKER_LABEL: workerLabel,
          ENV_VARS: envVarString
        )
        toolbox.slurpArtifacts(lms_unit_5)
      },
      {
        lms_unit_6 = build(
          subsetJob,
          sha1: sha1,
          SHARD: "6",
          TEST_SUITE: "lms-unit",
          PARENT_BUILD: "master #" + build.number,
          WORKER_LABEL: workerLabel,
          ENV_VARS: envVarString
        )
        toolbox.slurpArtifacts(lms_unit_6)
      },
      {
        lms_unit_7 = build(
          subsetJob,
          sha1: sha1,
          SHARD: "7",
          TEST_SUITE: "lms-unit",
          PARENT_BUILD: "master #" + build.number,
          WORKER_LABEL: workerLabel,
          ENV_VARS: envVarString
        )
        toolbox.slurpArtifacts(lms_unit_7)
      },
      {
        lms_unit_8 = build(
          subsetJob,
          sha1: sha1,
          SHARD: "8",
          TEST_SUITE: "lms-unit",
          PARENT_BUILD: "master #" + build.number,
          WORKER_LABEL: workerLabel,
          ENV_VARS: envVarString
        )
        toolbox.slurpArtifacts(lms_unit_8)
      },
      {
        lms_unit_9 = build(
          subsetJob,
          sha1: sha1,
          SHARD: "9",
          TEST_SUITE: "lms-unit",
          PARENT_BUILD: "master #" + build.number,
          WORKER_LABEL: workerLabel,
          ENV_VARS: envVarString
        )
        toolbox.slurpArtifacts(lms_unit_9)
      },
      {
        lms_unit_10 = build(
          subsetJob,
          sha1: sha1,
          SHARD: "10",
          TEST_SUITE: "lms-unit",
          PARENT_BUILD: "master #" + build.number,
          WORKER_LABEL: workerLabel,
          ENV_VARS: envVarString
        )
        toolbox.slurpArtifacts(lms_unit_10)
      },
      {
        cms_unit_1 = build(
          subsetJob,
          sha1: sha1,
          SHARD: "1",
          TEST_SUITE: "cms-unit",
          PARENT_BUILD: "master #" + build.number,
          WORKER_LABEL: workerLabel,
          ENV_VARS: envVarString
        )
        toolbox.slurpArtifacts(cms_unit_1)
      },
      {
        cms_unit_2 = build(
          subsetJob,
          sha1: sha1,
          SHARD: "2",
          TEST_SUITE: "cms-unit",
          PARENT_BUILD: "master #" + build.number,
          WORKER_LABEL: workerLabel,
          ENV_VARS: envVarString
        )
        toolbox.slurpArtifacts(cms_unit_2)
      },
      {
        commonlib_unit_1 = build(
          subsetJob,
          sha1: sha1,
          SHARD: "1",
          TEST_SUITE: "commonlib-unit",
          PARENT_BUILD: "master #" + build.number,
          WORKER_LABEL: workerLabel,
          ENV_VARS: envVarString
        )
        toolbox.slurpArtifacts(commonlib_unit_1)
      },
      {
        commonlib_unit_2 = build(
          subsetJob,
          sha1: sha1,
          SHARD: "2",
          TEST_SUITE: "commonlib-unit",
          PARENT_BUILD: "master #" + build.number,
          WORKER_LABEL: workerLabel,
          ENV_VARS: envVarString
        )
        toolbox.slurpArtifacts(commonlib_unit_2)
      },
      {
        commonlib_unit_3 = build(
          subsetJob,
          sha1: sha1,
          SHARD: "3",
          TEST_SUITE: "commonlib-unit",
          PARENT_BUILD: "master #" + build.number,
          WORKER_LABEL: workerLabel,
          ENV_VARS: envVarString
        )
        toolbox.slurpArtifacts(commonlib_unit_3)
      },
    )

    check_coverage = (
      lms_unit_1.result.toString() == 'SUCCESS' &&
      lms_unit_2.result.toString() == 'SUCCESS' &&
      lms_unit_3.result.toString() == 'SUCCESS' &&
      lms_unit_4.result.toString() == 'SUCCESS' &&
      lms_unit_5.result.toString() == 'SUCCESS' &&
      lms_unit_6.result.toString() == 'SUCCESS' &&
      lms_unit_7.result.toString() == 'SUCCESS' &&
      lms_unit_8.result.toString() == 'SUCCESS' &&
      lms_unit_9.result.toString() == 'SUCCESS' &&
      lms_unit_10.result.toString() == 'SUCCESS' &&
      cms_unit_1.result.toString() == 'SUCCESS' &&
      cms_unit_2.result.toString() == 'SUCCESS' &&
      commonlib_unit_1.result.toString() == 'SUCCESS' &&
      commonlib_unit_2.result.toString() == 'SUCCESS' &&
      commonlib_unit_3.result.toString() == 'SUCCESS' &&
      runCoverage.toBoolean()
    )

    if (check_coverage){
      unit_coverage = build(coverageJob,
                            UNIT_BUILD_NUM_1: commonlib_unit_1.number,
                            UNIT_BUILD_NUM_2: commonlib_unit_2.number,
                            UNIT_BUILD_NUM_3: commonlib_unit_3.number,
                            UNIT_BUILD_NUM_4: lms_unit_1.number,
                            UNIT_BUILD_NUM_5: lms_unit_2.number,
                            UNIT_BUILD_NUM_6: lms_unit_3.number,
                            UNIT_BUILD_NUM_7: lms_unit_4.number,
                            UNIT_BUILD_NUM_8: lms_unit_5.number,
                            UNIT_BUILD_NUM_9: lms_unit_6.number,
                            UNIT_BUILD_NUM_10: lms_unit_7.number,
                            UNIT_BUILD_NUM_11: lms_unit_8.number,
                            UNIT_BUILD_NUM_12: lms_unit_9.number,
                            UNIT_BUILD_NUM_13: lms_unit_10.number,
                            UNIT_BUILD_NUM_14: cms_unit_1.number,
                            UNIT_BUILD_NUM_15: cms_unit_2.number,
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
