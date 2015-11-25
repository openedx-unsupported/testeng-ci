""" Helper exception """


class Aborted(Exception):
    """
    Exception used to escape from operations that are being mocked
    or intercepted and should abort
    """
    pass
