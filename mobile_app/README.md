Mobile Apps
===========

Tools contained here are used for working with the mobile-apps

trigger_build
-------------
This will:

* Write a known set of environment variables to disk in JSON format to a file
  named CONFIGURATION.
* Create a new commit with that environment and push to origin.

This will in turn trigger a CI job which makes a new build with that commit,
providing access to that environment. The goal is to let a job be triggered in
various ways, particularly jenkins, but have the actual build step be run on a
separate build machine.

*Usage*

* Create your virtual environment
* Export the necessary environment variables. There's a list inside the script.
* pip install -r mobile_app/requirements.txt
* Call script as a python module, e.g.

	`python -m mobile_app.trigger_build --branch-name UniqueBranchName --trigger-repo-path ../my-repo`


The expectation is that the branch name will be some unique identifier like the
jenkins job number and the date.
	
