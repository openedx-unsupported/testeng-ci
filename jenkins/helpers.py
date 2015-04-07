"""
Helpers for jenkins api
"""


def append_url(base, addition):
    """
    Add something to a url, ensuring that there are the
    right amount of `/`.

    :Args:
        base: The original url.
        addition: the thing to add to the end of the url

    :Returns: The combined url as a string of the form
        `base/addition`
    """
    if not base.endswith('/'):
        base += '/'
    if addition.startswith('/'):
        addition = addition[1:]
    return base + addition
