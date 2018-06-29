# testeng-ci

### About

This repo contains the scripts and tools we use at edX to maintain our build infrastructure, specifically related to managing our Jenkins infrastructure, gathering data on our usage of Travis, and for testing browser performance as part of our [edx-platform](https://github.com/edx/edx-platform) CI.

This repo contains:

* Scripts that do things like:
	* Find all Travis builds on a given github org (like edx) and report on status + counts
	* Clean up orphaned jenkins-worker nodes with whom we have lost contact
	* build-flow scripts used in Jenkins edx-platform jobs
	* release infrastructure for mobile builds

* Job infrastructure for our Jenkins instance


