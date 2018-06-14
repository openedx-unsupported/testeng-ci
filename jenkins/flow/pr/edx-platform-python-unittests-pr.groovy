import hudson.FilePath
import hudson.model.*

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("ghprbActualCommit")
def branch = build.environment.get("ghprbSourceBranch")
def subsetJob = build.environment.get("SUBSET_JOB") ?: "edx-platform-test-subset"
def coverageJob = build.environment.get("COVERAGE_JOB") ?: "edx-platform-unit-coverage"
def workerLabel = build.environment.get("WORKER_LABEL") ?: "jenkins-worker"
def toxEnv = build.environment.get("TOX_ENV") ?: ""
def targetBranch = build.environment.get("TARGET_BRANCH") ?: "origin/master"
def runCoverage = build.environment.get("RUN_COVERAGE") ?: "true"

// Any environment variables that you want to inject into the environment of
// child jobs of this build flow should be added here (comma-separated,
// in the format VARIABLE=VALUE)
def envVarString = "TOX_ENV=${toxEnv}, RUN_COVERAGE=${runCoverage}"

guard{
    unit = parallel(
      {
        lms_unit_1 = build(subsetJob,
                           sha1: sha1,
                           SHARD: "1",
                           TEST_SUITE: "lms-unit",
                           PARENT_BUILD: "PR Build #" + build.number,
                           WORKER_LABEL: workerLabel,
                           ENV_VARS: envVarString
                           )
        toolbox.slurpArtifacts(lms_unit_1)
      },
      {
        lms_unit_2 = build(subsetJob,
                           sha1: sha1,
                           SHARD: "2",
                           TEST_SUITE: "lms-unit",
                           PARENT_BUILD: "PR Build #" + build.number,
                           WORKER_LABEL: workerLabel,
                           ENV_VARS: envVarString
                           )
        toolbox.slurpArtifacts(lms_unit_2)
      },
      {
        lms_unit_3 = build(subsetJob,
                           sha1: sha1,
                           SHARD: "3",
                           TEST_SUITE: "lms-unit",
                           PARENT_BUILD: "PR Build #" + build.number,
                           WORKER_LABEL: workerLabel,
                           ENV_VARS: envVarString
                           )
        toolbox.slurpArtifacts(lms_unit_3)
      },
      {
        lms_unit_4 = build(subsetJob,
                           sha1: sha1,
                           SHARD: "4",
                           TEST_SUITE: "lms-unit",
                           PARENT_BUILD: "PR Build #" + build.number,
                           WORKER_LABEL: workerLabel,
                           ENV_VARS: envVarString
                           )
        toolbox.slurpArtifacts(lms_unit_4)
      },
      {
        lms_unit_5 = build(subsetJob,
                           sha1: sha1,
                           SHARD: "5",
                           TEST_SUITE: "lms-unit",
                           PARENT_BUILD: "PR Build #" + build.number,
                           WORKER_LABEL: workerLabel,
                           ENV_VARS: envVarString
                           )
        toolbox.slurpArtifacts(lms_unit_5)
      },
      {
        lms_unit_6 = build(subsetJob,
                           sha1: sha1,
                           SHARD: "6",
                           TEST_SUITE: "lms-unit",
                           PARENT_BUILD: "PR Build #" + build.number,
                           WORKER_LABEL: workerLabel,
                           ENV_VARS: envVarString
                           )
        toolbox.slurpArtifacts(lms_unit_6)
      },
      {
        lms_unit_7 = build(subsetJob,
                           sha1: sha1,
                           SHARD: "7",
                           TEST_SUITE: "lms-unit",
                           PARENT_BUILD: "PR Build #" + build.number,
                           WORKER_LABEL: workerLabel,
                           ENV_VARS: envVarString
                           )
        toolbox.slurpArtifacts(lms_unit_7)
      },
      {
        lms_unit_8 = build(subsetJob,
                           sha1: sha1,
                           SHARD: "8",
                           TEST_SUITE: "lms-unit",
                           PARENT_BUILD: "PR Build #" + build.number,
                           WORKER_LABEL: workerLabel,
                           ENV_VARS: envVarString
                           )
        toolbox.slurpArtifacts(lms_unit_8)
      },
      {
        lms_unit_9 = build(subsetJob,
                           sha1: sha1,
                           SHARD: "9",
                           TEST_SUITE: "lms-unit",
                           PARENT_BUILD: "PR Build #" + build.number,
                           WORKER_LABEL: workerLabel,
                           ENV_VARS: envVarString
                           )
        toolbox.slurpArtifacts(lms_unit_9)
      },
      {
        lms_unit_10 = build(subsetJob,
                           sha1: sha1,
                           SHARD: "10",
                           TEST_SUITE: "lms-unit",
                           PARENT_BUILD: "PR Build #" + build.number,
                           WORKER_LABEL: workerLabel,
                           ENV_VARS: envVarString
                           )
        toolbox.slurpArtifacts(lms_unit_10)
      },
      {
        cms_unit_1 = build(subsetJob,
                           sha1: sha1,
                           SHARD: "1",
                           TEST_SUITE: "cms-unit",
                           PARENT_BUILD: "PR Build #" + build.number,
                           WORKER_LABEL: workerLabel,
                           ENV_VARS: envVarString
                           )
        toolbox.slurpArtifacts(cms_unit_1)
      },
      {
        cms_unit_2 = build(subsetJob,
                           sha1: sha1,
                           SHARD: "2",
                           TEST_SUITE: "cms-unit",
                           PARENT_BUILD: "PR Build #" + build.number,
                           WORKER_LABEL: workerLabel,
                           ENV_VARS: envVarString
                           )
        toolbox.slurpArtifacts(cms_unit_2)
      },
      {
        commonlib_unit_1 = build(subsetJob,
                               sha1: sha1,
                               SHARD: "1",
                               TEST_SUITE: "commonlib-unit",
                               PARENT_BUILD: "PR Build #" + build.number,
                               WORKER_LABEL: workerLabel,
                               ENV_VARS: envVarString
                               )
        toolbox.slurpArtifacts(commonlib_unit_1)
      },
      {
        commonlib_unit_2 = build(subsetJob,
                               sha1: sha1,
                               SHARD: "2",
                               TEST_SUITE: "commonlib-unit",
                               PARENT_BUILD: "pr build #" + build.number,
                               WORKER_LABEL: workerLabel,
                               ENV_VARS: envVarString
                               )
        toolbox.slurpArtifacts(commonlib_unit_2)
      },
      {
        commonlib_unit_3 = build(subsetJob,
                               sha1: sha1,
                               SHARD: "3",
                               TEST_SUITE: "commonlib-unit",
                               PARENT_BUILD: "pr build #" + build.number,
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
                            PARENT_BUILD: "PR Build #" + build.number,
                            CI_BRANCH: branch,
                            TARGET_BRANCH: targetBranch
                           )

      toolbox.slurpArtifacts(unit_coverage)
    }
}rescue{
    FilePath artifactsDir =  new FilePath(build.artifactManager.getArtifactsDir())
    artifactsDir.copyRecursiveTo(build.workspace)

    // Delete the report artifacts that we copied into the staging area, to reduce
    // disk usage. These are copied by the HTML Publisher plugin and the
    // Shining Panda Coverage plugin, and these are redundant. However, leave
    // the 'test_root' directory, as it is indexed by Splunk for paver timing
    // reports
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
