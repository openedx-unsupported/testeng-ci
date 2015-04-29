from unittest import TestCase

from jenkins.tests.helpers import sample_data, Pr
from jenkins.build import Build


class BuildTestCase(TestCase):
    """
    TestCase class for testing the Build class
    """

    def setUp(self):
        self.sample_build_data = sample_data(
            [Pr('2', author='bar').dict],
            []
        )['builds'][0]

    def test_init_build(self):
        build = Build(self.sample_build_data)
        self.assertEqual(build.author, 'bar')
        self.assertEqual(build.pr_id, '2')
        self.assertTrue(build.isbuilding)

    def test_init_build_with_missing_params(self):
        self.sample_build_data['actions'][0] = {}
        build = Build(self.sample_build_data)
        self.assertIsNone(build.author)
        self.assertIsNone(build.pr_id)
        self.assertTrue(build.isbuilding)
