"""
Given a directory, look for files that aren't python 3
and chunk them into 10 file chunks.

Produce a CSV that can be imported into jira to make ticets
for converting each 10 file batch.

Pass in as an arg the directory to look under.
"""

from __future__ import print_function

import csv
import os
import sys

FILE_LIMIT = 10

def filter_python_files(files):
    """
    given a list of files, extract the python files
    """
    return [f for f in files if f.endswith('.py')]


def filter_valid_files(root, files):
    """
    given a root directory and files in it, do all relevant filtering
    to find files that still need to be converted.
    """

    for filename in filter_python_files(files):
        ## Check to see if the file has already been converted.
        #import pudb; pu.db
        file_path = os.path.join(root, filename)
        file_is_python_3 = False
        with open(file_path, 'r') as f:
            for line in f.readlines():
                if "from __future__ import" in line and " absolute_import" in line:
                    file_is_python_3 = True
                    break

        if not file_is_python_3:
            yield filename


def get_file_chunks(root_dir):
    file_list = []
    for root, dirs, files in os.walk(root_dir, topdown=False):
        if root.startswith(os.path.join(root_dir, ".git")):
            # Skip everything in the .git directory
            continue

        for unconverted_file in filter_valid_files(root, files):
            fullpath = os.path.join(root, unconverted_file)
            relative_path = os.path.relpath(fullpath, root_dir)
            file_list.append(relative_path)
            if len(file_list) >= FILE_LIMIT:
                yield file_list
                file_list = []

SUMMARY = "Run python-modernize on edx-platform ({} of {})"
DESCRIPTION_TEMPLATE = \
"""Help prepare edx-platform for python3 by doing the following:

# Comment on the ticket to indicate that you are starting work on it.
# Launch a development shell in a Docker container via either "make shell" or devstack's "make lms-shell". Alternatively, you can create a new virtualenv or conda environment and install modernize and isort into it (this is a better choice on Windows).
# run 
{{code}}
python-modernize -w {file_list}
{{code}}
# run 
{{code}}
isort -rc {file_list}
{{code}}
# Make sure the changes look reasonable and submit them as a pull request; mention this ticket in the description and include INCR-<Ticket Number> in the name.
# Ask for tests to be triggered if they don't start automatically.
# Diagnose any test failures caused by the changes, and either fix them or ask for help.
# If you run into unexpected errors, see this document for common problems: https://openedx.atlassian.net/wiki/spaces/AC/pages/977666218/Using+python-modernize+effectively"""






if __name__ == "__main__":
    enumeration_start = 222
    file_chunks = list(get_file_chunks(sys.argv[1]))
    total_number_of_tickets = len(file_chunks) + enumeration_start -1

    with open("chunk_tickets.csv", 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter="|")
        csvwriter.writerow(["Epic Link", "Issue Type", "Summary", "Description"])

        for number, file_chunk in enumerate(file_chunks, start=enumeration_start):
            csvwriter.writerow([
		"INCR-1",
		"Task",
		SUMMARY.format(number, total_number_of_tickets),
		DESCRIPTION_TEMPLATE.format(file_list=" ".join(file_chunk)),
	    ])
