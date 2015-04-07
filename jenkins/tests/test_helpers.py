from unittest import TestCase

from jenkins.helpers import append_url


class HelpersTestCase(TestCase):

    def test_append_url(self):
        expected = 'http://my_base_url.com/the_extra_part'
        inputs = [
            ('http://my_base_url.com', 'the_extra_part'),
            ('http://my_base_url.com', '/the_extra_part'),
            ('http://my_base_url.com/', 'the_extra_part'),
            ('http://my_base_url.com/', '/the_extra_part'),
        ]

        for i in inputs:
            returned = append_url(*i)
            self.assertEqual(
                expected,
                returned,
                msg="{e} != {r}\nInputs: {i}".format(
                    e=expected, r=returned, i=str(i)
                )
            )
