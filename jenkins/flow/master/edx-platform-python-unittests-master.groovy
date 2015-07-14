import hudson.FilePath
import hudson.model.*

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("GIT_COMMIT")

try{
  def statusJobParams = [
    new StringParameterValue("GITHUB_ORG", "edx"),
    new StringParameterValue("GITHUB_REPO", "edx-platform"),
    new StringParameterValue("GIT_SHA", "${sha1}"),
    new StringParameterValue("BUILD_STATUS", "pending"),
    new StringParameterValue("TARGET_URL", "https://build.testeng.edx.org/job/edx-platform-python-unittests-master/${build.number}"),
    new StringParameterValue("DESCRIPTION", "Pending"),
    new StringParameterValue("CONTEXT", "jenkins/python"),
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
    unit = parallel(
      {
        lms_unit_1 = build('edx-platform-test-subset', sha1: sha1, SHARD: "1", TEST_SUITE: "lms-unit", PARENT_BUILD: "master #" + build.number)
        toolbox.slurpArtifacts(lms_unit_1)
      },
      {
        lms_unit_2 = build('edx-platform-test-subset', sha1: sha1, SHARD: "2", TEST_SUITE: "lms-unit", PARENT_BUILD: "master #" + build.number)
        toolbox.slurpArtifacts(lms_unit_2)
      },
      {
        cms_unit = build('edx-platform-test-subset', sha1: sha1, SHARD: "1", TEST_SUITE: "cms-unit", PARENT_BUILD: "master #" + build.number)
        toolbox.slurpArtifacts(cms_unit)
      },
      {
        commonlib_unit = build('edx-platform-test-subset', sha1: sha1, SHARD: "1", TEST_SUITE: "commonlib-unit", PARENT_BUILD: "master #" + build.number)
        toolbox.slurpArtifacts(commonlib_unit)
      },
    )

    check_coverage = (
      lms_unit_1.result.toString() == 'SUCCESS' &&
      lms_unit_2.result.toString() == 'SUCCESS' &&
      cms_unit.result.toString() == 'SUCCESS' &&
      commonlib_unit.result.toString() == 'SUCCESS')

    if (check_coverage){
      unit_coverage = build('edx-platform-unit-coverage',
                            UNIT_BUILD_NUM_1: commonlib_unit.number,
                            UNIT_BUILD_NUM_2: lms_unit_1.number,
                            UNIT_BUILD_NUM_3: lms_unit_2.number,
                            UNIT_BUILD_NUM_4: cms_unit.number,
                            sha1: sha1,
                            PARENT_BUILD: "master #" + build.number,
                            CI_BRANCH: "master"
                           )

      toolbox.slurpArtifacts(unit_coverage)
    }
  }rescue{
    FilePath artifactsDir =  new FilePath(build.artifactManager.getArtifactsDir())
    artifactsDir.copyRecursiveTo(build.workspace)
  }
}
