#!/usr/bin/env bash
set -e

: ${GITHUB_USER:?"The GITHUB_USER environment variable must be set."}
: ${GITHUB_PASS:?"The GITHUB_PASS environment variable must be set."}


virtualenv push_fork_venv -q
source push_fork_venv/bin/activate
echo "Installing python requirements..."
pip install -q pygithub==1.2.5

python push-fork.py -u $GITHUB_USER -p $GITHUB_PASS
