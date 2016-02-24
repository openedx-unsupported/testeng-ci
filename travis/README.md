Travis Build Metrics
=====

Tools contained here are used for obtaining metadata of Travis builds

build_info
---
This script will:

* use the Travis REST API to get information on builds.

*Usage*

* create your virtual environment
* pip install -r travis/requirements.txt
* Call script as a python module, e.g.

	`python -m travis.build_info --org MyGithubOrg --log_level debug`
	