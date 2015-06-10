import hudson.FilePath

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("ghprbActualCommit")

guard{
  parallel(
    {
      bok_choy_1 = build('edx-platform-test-subset', sha1: sha1, SHARD: "1", TEST_SUITE: "bok-choy", PARENT_BUILD: "PR Build #" + build.number)
      toolbox.slurpArtifacts(bok_choy_1)
    },
    {
      bok_choy_2 = build('edx-platform-test-subset', sha1: sha1, SHARD: "2", TEST_SUITE: "bok-choy", PARENT_BUILD: "PR Build #" + build.number)
      toolbox.slurpArtifacts(bok_choy_2)
    },
    {
      bok_choy_3 = build('edx-platform-test-subset', sha1: sha1, SHARD: "3", TEST_SUITE: "bok-choy", PARENT_BUILD: "PR Build #" + build.number)
      toolbox.slurpArtifacts(bok_choy_3)
    },
    {
      bok_choy_4 = build('edx-platform-test-subset', sha1: sha1, SHARD: "4", TEST_SUITE: "bok-choy", PARENT_BUILD: "PR Build #" + build.number)
      toolbox.slurpArtifacts(bok_choy_4)
    },
    {
      bok_choy_5 = build('edx-platform-test-subset', sha1: sha1, SHARD: "5", TEST_SUITE: "bok-choy", PARENT_BUILD: "PR Build #" + build.number)
      toolbox.slurpArtifacts(bok_choy_5)
    }, 
    {
      bok_choy_6 = build('edx-platform-test-subset', sha1: sha1, SHARD: "6", TEST_SUITE: "bok-choy", PARENT_BUILD: "PR Build #" + build.number)
      toolbox.slurpArtifacts(bok_choy_6)
    }, 
    {
      unit = parallel(
        {
          lms_unit_1 = build('edx-platform-test-subset', sha1: sha1, SHARD: "1", TEST_SUITE: "lms-unit", PARENT_BUILD: "PR Build #" + build.number)
          toolbox.slurpArtifacts(lms_unit_1)
        },
        {
          lms_unit_2 = build('edx-platform-test-subset', sha1: sha1, SHARD: "2", TEST_SUITE: "lms-unit", PARENT_BUILD: "PR Build #" + build.number)
          toolbox.slurpArtifacts(lms_unit_2)
        },
        {
          cms_unit = build('edx-platform-test-subset', sha1: sha1, SHARD: "1", TEST_SUITE: "cms-unit", PARENT_BUILD: "PR Build #" + build.number)
          toolbox.slurpArtifacts(cms_unit)
        },
        {
          commonlib_js_unit = build('edx-platform-test-subset', sha1: sha1, SHARD: "1", TEST_SUITE: "commonlib-js-unit", PARENT_BUILD: "PR Build #" + build.number)
          toolbox.slurpArtifacts(commonlib_js_unit)
        },
      )

      check_coverage = (
        lms_unit_1.result.toString() == 'SUCCESS' &&
        lms_unit_2.result.toString() == 'SUCCESS' &&
        cms_unit.result.toString() == 'SUCCESS' &&
        commonlib_js_unit.result.toString() == 'SUCCESS')

      if (check_coverage){
        unit_coverage = build('edx-platform-unit-coverage',
                              UNIT_BUILD_NUM_1: commonlib_js_unit.number,
                              UNIT_BUILD_NUM_2: lms_unit_1.number,
                              UNIT_BUILD_NUM_3: lms_unit_2.number,
                              UNIT_BUILD_NUM_4: cms_unit.number,
                              sha1: sha1,
                              PARENT_BUILD: "PR Build #" + build.number)

        toolbox.slurpArtifacts(unit_coverage)
      }
    },
    {
      lettuce_lms = build('edx-platform-test-subset', sha1: sha1, SHARD: "all", TEST_SUITE: "lms-acceptance", PARENT_BUILD: "PR Build #" + build.number)
      toolbox.slurpArtifacts(lettuce_lms)
    },
    {
      lettuce_cms = build('edx-platform-test-subset', sha1: sha1, SHARD: "all", TEST_SUITE: "cms-acceptance", PARENT_BUILD: "PR Build #" + build.number)
      toolbox.slurpArtifacts(lettuce_cms)
    },
    {
      quality = build('edx-platform-test-subset', sha1: sha1, SHARD: "", TEST_SUITE: "quality", PARENT_BUILD: "PR Build #" + build.number)  
      toolbox.slurpArtifacts(quality)
    },
  )
}rescue{
  FilePath artifactsDir =  new FilePath(build.artifactManager.getArtifactsDir())
  artifactsDir.copyRecursiveTo(build.workspace)
}
