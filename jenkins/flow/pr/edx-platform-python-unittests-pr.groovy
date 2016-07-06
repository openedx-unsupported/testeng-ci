import hudson.FilePath
import hudson.model.*

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("ghprbActualCommit")
def branch = build.environment.get("ghprbSourceBranch")
def job = build.environment.get("JOB_NAME")

if (job.contains("private")) {
    subsetJob = "edx-platform-test-subset_private"
    platformName = "edx-platform-private"
}
else {
    subsetJob = "edx-platform-test-subset"
    platformName = "edx-platform"
}
{
    unit = parallel(
      {
        lms_unit_1 = build(subsetJob, sha1: sha1, SHARD: "1", TEST_SUITE: "lms-unit", PARENT_BUILD: "PR Build #" + build.number)
        toolbox.slurpArtifacts(lms_unit_1)
      },
      {
        lms_unit_2 = build(subsetJob, sha1: sha1, SHARD: "2", TEST_SUITE: "lms-unit", PARENT_BUILD: "PR Build #" + build.number)
        toolbox.slurpArtifacts(lms_unit_2)
      },
      {
        lms_unit_3 = build(subsetJob, sha1: sha1, SHARD: "3", TEST_SUITE: "lms-unit", PARENT_BUILD: "PR Build #" + build.number)
        toolbox.slurpArtifacts(lms_unit_3)
      },
      {
        lms_unit_4 = build(subsetJob, sha1: sha1, SHARD: "4", TEST_SUITE: "lms-unit", PARENT_BUILD: "PR Build #" + build.number)
        toolbox.slurpArtifacts(lms_unit_4)
      },
      {
        cms_unit = build(subsetJob, sha1: sha1, SHARD: "1", TEST_SUITE: "cms-unit", PARENT_BUILD: "PR Build #" + build.number)
        toolbox.slurpArtifacts(cms_unit)
      },
      {
        commonlib_unit = build(subsetJob, sha1: sha1, SHARD: "1", TEST_SUITE: "commonlib-unit", PARENT_BUILD: "PR Build #" + build.number)
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
      unit_coverage = build('edx-platform-unit-coverage',
                            UNIT_BUILD_NUM_1: commonlib_unit.number,
                            UNIT_BUILD_NUM_2: lms_unit_1.number,
                            UNIT_BUILD_NUM_3: lms_unit_2.number,
                            UNIT_BUILD_NUM_4: lms_unit_3.number,
                            UNIT_BUILD_NUM_5: lms_unit_4.number,
                            UNIT_BUILD_NUM_6: cms_unit.number,
                            sha1: sha1,
                            PARENT_BUILD: "PR Build #" + build.number,
                            CI_BRANCH: branch,
                           )

      toolbox.slurpArtifacts(unit_coverage)
    }
}rescue{
    FilePath artifactsDir =  new FilePath(build.artifactManager.getArtifactsDir())
    FilePath copyToDir = new FilePath(build.workspace, platformName)
    artifactsDir.copyRecursiveTo(copyToDir)
}
