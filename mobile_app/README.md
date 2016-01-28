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
* pip install -r mobile_app/requirements.txt
* Export the necessary environment variables. There's a list inside the script.
* Call script as a python module, e.g.

	`python -m mobile_app.trigger_build --branch-name UniqueBranchName --trigger-repo-path ../my-repo`


The expectation is that the branch name will be some unique identifier like the
jenkins job number and the date.
	

checkout_build_repos
--------------------

Checks out a code and config repository and sets them up for building, by creating a properties file to point the code at the config.

*Usage*
* Create your virtual environment
* pip install -r mobile_app/requirements.txt
* Create a file called ``CONFIGURATION``. See ``trigger_build`` for more information on the format.
* Call script as a python module,
    e.g.

    `python -m mobile_app.checkout_build_repos`

This will result in two new folders, "code.git" and "config.git" cloned from the code and config URLs in CONFIGURATION. They will be checked out to the revision specified in CONFIGURATION.
