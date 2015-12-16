Release Tools
=====

Tools contained here are used for continuous delivery pipelines at edX.

create_candidate_pr
---
This script will:

* Remotely create a release candidate (rc) branch according to a naming convention
* Create a pull request with that rc branch against the 'release' branch

*Usage*

* create your virtual environment
* pip install -r release/requirements.txt
* Call script as a python module, e.g.

	`python -m release.create_candidate_pr --org MyGithubOrg --repo my-repo`
	