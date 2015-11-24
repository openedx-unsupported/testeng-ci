"""
Tests for testeng-ci/release/utils
"""
from datetime import datetime
from mock import patch, Mock
from unittest import TestCase

import release.utils


class ReleaseUtilsTestCase(TestCase):
    """ Test Cases for release utility functions """

    def mock_now(self, now=datetime(year=1983, month=12, day=7, hour=6)):
        """ Patches datetime.now to provide the given date """
        # datetime.now can't be patched directly
        # so we have to go through this indirect route
        datetime_patcher = patch.object(
            release.utils, 'datetime',
            Mock(wraps=datetime)
        )
        mocked_datetime = datetime_patcher.start()
        mocked_datetime.now.return_value = now
        self.addCleanup(datetime_patcher.stop)
        return now

    def test_start_after_current_day(self):
        """ Tests that we don't start on the current day """
        now = self.mock_now()
        date = release.utils.default_expected_release_date(now.weekday())
        self.assertEqual(date.weekday(), now.weekday())
        self.assertTrue(now < date)
