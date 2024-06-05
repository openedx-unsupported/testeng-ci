# testeng-ci

⚠️⚠️⚠️⚠️ **THIS REPOSITORY IS DEPRECATED** ⚠️⚠️⚠️⚠️

This PR Creator script has been moved to [Open edX repo-tools](https://github.com/openedx/repo-tools).

The other tools have been moved from edX's Jenkins infrastructure into GitHub Actions workflows.

Details: https://github.com/openedx/public-engineering/issues/265

## About

This repo contains a script to programmatically create GitHub pull requests, used in GitHub Actions such as the ones used to periodically update Python dependencies in most of our repositories.

It used to also contain the scripts and tools we used at edX to maintain our build infrastructure, specifically related to managing our Jenkins infrastructure, gathering data on our usage of Travis, and for testing browser performance as part of our [edx-platform](https://github.com/edx/edx-platform) CI.  This explains the naming choices which seem incongruent with the current repository content.
