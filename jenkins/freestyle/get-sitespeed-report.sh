#!/bin/bash
set -e

# Sitespeed job script
# Assumes that the required environment variables are set
# either by the jenkins job or in the shell
# Assumes the following environment variables are set
#
# EDX_USER - Registered edX user for logging in and creating the session cookie file
# EDX_PASS - Password for the registered edX user
# USE_BASIC_AUTH - Is the site secured with basic auth (e.g. sandboxes are)
# AUTH_USER (optional, required if USE_BASIC_AUTH) - Basic auth username
# AUTH_PASS (optional, required if USE_BASIC_AUTH) - Basic auth password
# NUMBER_OF_TIMES - The number of times to test each URL when fetching timing metrics
# CONNECTION - Limit the speed by simulating connection types
# SITESPEED_BROWSER - Which browser to use to collect timing data
#
# To specify the URL(s) to test, you must set either:
# TEST_URL - A single URL to test
# or
# GET_URLS_FROM_FILE - If this (string) value is (case sensitive) "true"
# TEST_URL_FILE - The name of the file containing URLs to test
#
# To (optionally) run using a budget, set the following variables:
# SITESPEED_USE_BUDGET - (string) value is (case sensitive) "true"
# SITESPEED_BUDGET_FILE - The name of the file containing the sitespeed budget
#      e.g. "testeng-ci/jenkins/freestyle/lms-budget.json"

# Verify required variables are set. The statements below will cause
# the script to exit with a non zero status if they are not.
: ${EDX_USER:?"The EDX_USER environment variable must be set."}
: ${EDX_PASS:?"The EDX_PASS environment variable must be set."}
: ${USE_BASIC_AUTH:?"The USE_BASIC_AUTH environment variable must be set."}
: ${NUMBER_OF_TIMES:?"The NUMBER_OF_TIMES environment variable must be set."}
: ${CONNECTION:?"The CONNECTION environment variable must be set."}
: ${SITESPEED_BROWSER:?"The SITESPEED_BROWSER environment variable must be set."}

# Test for the existence of TEST_URL_FILE
if [ ! -z ${TEST_URL_FILE+x} ] ; then

    if [ "$TEST_URL_FILE" == "" ] ; then
        echo "TEST_URL_FILE environment variable is set, but empty. Skipping related logic."

    else

    	# HACK: Copy the contents of the URL file to a file
    	# named "multiple_urls" and use that so that the output folder will
    	# have a known name ("results") and thus the artifacts can be
    	# archived correctly on jenkins
    	TMP_URL_FILE="/tmp/multiple_urls"
    	cp -rf "$TEST_URL_FILE" "$TMP_URL_FILE"

    	if [ ! -f $TMP_URL_FILE ]; then
            echo "ERROR: Could not copy '$TEST_URL_FILE' to '$TMP_URL_FILE'."
            exit 1
    	fi

    	# Use the URL from the first line of the URL file as the TEST_URL,
    	# in order to log in and capture the session information.
    	read -r TEST_URL< $TMP_URL_FILE
    fi
else
    # Verify that the TEST_URL environment was set either directly or
    # via the TEST_URL_FILE contents.
    : ${TEST_URL:?"The TEST_URL or TEST_URL_FILE environment variable must be set."}

fi


if [ $SITESPEED_USE_BUDGET == "true" ] ; then
	msg="The SITESPEED_BUDGET_FILE environment variable must be set to the json file containing the budget."
	: ${SITESPEED_BUDGET_FILE:?$msg}

	if [ ! -f $SITESPEED_BUDGET_FILE ]; then
	    echo "ERROR: Specified SITESPEED_BUDGET_FILE '$SITESPEED_BUDGET_FILE' does not exist."
	    exit 1
	fi
fi

echo "Cleaning out old results if they exist"
rm -rf sitespeed-result
mkdir sitespeed-result

# Use the url and credential information to log in and create a file with the session cookie data
ARGS="edx-sitespeed/edx_sitespeed/edx_sitespeed.py -e ${EDX_USER} -p ${EDX_PASS} -u ${TEST_URL}"
if [ $USE_BASIC_AUTH == "true" ] ; then
    ARGS="${ARGS} --auth_user ${AUTH_USER} --auth_pass ${AUTH_PASS}"
fi
echo "Recording the session cookie for a logged-in user"
echo "Using this command: python ${ARGS}"
python ${ARGS}

# Construct the command to run the test under sitespeed.io
if [ -f $TMP_URL_FILE ] ; then
    ARGS="-f ${TMP_URL_FILE}"
else
    ARGS="-u ${TEST_URL}"
fi

ARGS="${ARGS} --requestHeaders cookie.json --junit --suppressDomainFolder"
ARGS="${ARGS} --outputFolderName results --screenshot --storeJson"
ARGS="${ARGS} -d 0 -n ${NUMBER_OF_TIMES} --connection ${CONNECTION}"

if [ $SITESPEED_USE_BUDGET == "true" ] ; then
    ARGS="${ARGS} --budget ${SITESPEED_BUDGET_FILE}"
fi

# Only try to take the timings with an actual browser.
# Note that the -b option is what uses the NUMBER_OF_TIMES
# setting and it is also what does the HAR file capture.
if [ $SITESPEED_BROWSER != "headless" ] ; then
    ARGS="${ARGS} -b ${SITESPEED_BROWSER}"
fi

if [ $USE_BASIC_AUTH == "true" ] ; then
    ARGS="${ARGS} --basicAuth ${AUTH_USER}:${AUTH_PASS}"
fi

# This is the command with all the arguments defined as necessary.
CMD="sitespeed.io ${ARGS}"

# If we specify a browser other than "headless" (e.g. firefox)
# then we need to use xvfb to run the browser headlessly
if [ $SITESPEED_BROWSER != "headless" ] ; then
    CMD="xvfb-run $CMD"
fi

# With --junit, sitespeed.io outputs the junit results to console.
# Redirect them to a file instead so that a Jenkins plugin can interpret the results.
echo "Measuring client side performance with sitespeed"
echo "Using this command: ${CMD} > sitespeed-result/junit.xml"
${CMD} > sitespeed-result/junit.xml

# Cleanup
rm -rf cookie.json
