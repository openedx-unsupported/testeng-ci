import hudson.FilePath

def toolbox = extension."build-flow-toolbox"
def sha1 = build.environment.get("ghprbActualCommit")

guard{
  parallel(
    {
      bok_choy_1 = build('edx-platform-test-subset', sha1: sha1, SHARD: "1", TEST_SUITE: "bok-choy")
      toolbox.slurpArtifacts(bok_choy_1)
    },
    {
      bok_choy_2 = build('edx-platform-test-subset', sha1: sha1, SHARD: "2", TEST_SUITE: "bok-choy")
      toolbox.slurpArtifacts(bok_choy_2)
    },
    {
      bok_choy_3 = build('edx-platform-test-subset', sha1: sha1, SHARD: "3", TEST_SUITE: "bok-choy")
      toolbox.slurpArtifacts(bok_choy_3)
    },
    {
      bok_choy_4 = build('edx-platform-test-subset', sha1: sha1, SHARD: "4", TEST_SUITE: "bok-choy")
      toolbox.slurpArtifacts(bok_choy_4)
    },
    {
      bok_choy_5 = build('edx-platform-test-subset', sha1: sha1, SHARD: "5", TEST_SUITE: "bok-choy")
      toolbox.slurpArtifacts(bok_choy_5)
    }, 
    {
      bok_choy_6 = build('edx-platform-test-subset', sha1: sha1, SHARD: "6", TEST_SUITE: "bok-choy")
      toolbox.slurpArtifacts(bok_choy_6)
    }, 
    {
      unit = parallel(
        { 
          lms_unit = build('edx-platform-test-subset', sha1: sha1, SHARD: "lms", TEST_SUITE: "unit")
          toolbox.slurpArtifacts(lms_unit)
        },  
        {
          other_unit = build('edx-platform-test-subset', sha1: sha1, SHARD: "cms-js-commonlib", TEST_SUITE: "unit") 
          toolbox.slurpArtifacts(other_unit)
        },
      )

      if (lms_unit.result.toString()  == 'SUCCESS' && other_unit.result.toString()  == 'SUCCESS'){      
      	unit_coverage = build('edx-platform-unit-coverage', UNIT_BUILD_NUM_1: other_unit.number, UNIT_BUILD_NUM_2: lms_unit.number, sha1: sha1)
      	toolbox.slurpArtifacts(unit_coverage)
      }
    },
    {
      lettuce_lms = build('edx-platform-test-subset', sha1: sha1, SHARD: "all", TEST_SUITE: "lms-acceptance")
      toolbox.slurpArtifacts(lettuce_lms)
    },
    {
      lettuce_cms = build('edx-platform-test-subset', sha1: sha1, SHARD: "all", TEST_SUITE: "cms-acceptance")
      toolbox.slurpArtifacts(lettuce_cms)
    },
    {
      quality = build('edx-platform-test-subset', sha1: sha1, SHARD: "", TEST_SUITE: "quality")  
      toolbox.slurpArtifacts(quality)
  
    },
  )
}rescue{
  FilePath artifactsDir =  new FilePath(build.artifactManager.getArtifactsDir())
  artifactsDir.copyRecursiveTo(build.workspace)
}
