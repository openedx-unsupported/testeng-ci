""" Assorted helpers for release tools """
from datetime import datetime, timedelta

# Day of week constant
_TUESDAY = 1
_NORMAL_RELEASE_WEEKDAY = _TUESDAY


def default_expected_release_date(release_day=_NORMAL_RELEASE_WEEKDAY):
    """
    Returns the default expected release date given the current date.
    Currently the nearest Tuesday in the future (can't be today)
    """
    proposal = datetime.now() + timedelta(days=1)
    while proposal.weekday() is not release_day:
        proposal = proposal + timedelta(days=1)
    return proposal
