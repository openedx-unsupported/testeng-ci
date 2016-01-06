#!/bin/bash
set -e

# Sitespeed job script
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
# One of the following environment variables should be set.
# To specify the URL(s) to test, you must set either:
# TEST_URL - A single URL to test
# or
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

# Test that the TEST_URL_FILE variable is set and not null.
# This is done by using bash parameter subsitution. If it is both set and not null, then x will substitute
# for TEST_URL_FILE, resulting in a value that is greater than zero-length.
# If TEST_URL_FILE is null or not set, then the parameter substitution
# would result in a zero-length var.
# See additional info here: https://www.gnu.org/software/bash/manual/html_node/Shell-Parameter-Expansion.html
if [[ ! -z ${TEST_URL_FILE+x} ]] ; then

    if [[ "$TEST_URL_FILE" == "" ]] ; then
        echo "TEST_URL_FILE environment variable is set, but empty. Skipping related logic."

    else

        # HACK: Copy the contents of the URL file to a file
        # named "multiple_urls" and use that so that the output folder will
        # have a known name (like "multiple_urls") and thus the artifacts can be
        # archived correctly on jenkins
        TMP_URL_FILE="/tmp/multiple_urls"
        cp -rf "$TEST_URL_FILE" "$TMP_URL_FILE"

        if [[ ! -f $TMP_URL_FILE ]]; then
            echo "ERROR: Could not copy '$TEST_URL_FILE' to '$TMP_URL_FILE'."
            exit 1
        fi

        # Use the URL from the first line of the URL file as the TEST_URL,
        # in order to log in and capture the session information.
        read -r TEST_URL< $TMP_URL_FILE
    fi
else
    # Verify that the TEST_URL environment variable was set either directly or
    # via the TEST_URL_FILE contents.
    : ${TEST_URL:?"The TEST_URL or TEST_URL_FILE environment variable must be set."}

fi


if [[ $SITESPEED_USE_BUDGET == "true" ]] ; then
    msg="The SITESPEED_BUDGET_FILE environment variable must be set to the json file containing the budget."
    : ${SITESPEED_BUDGET_FILE:?$msg}

    if [[ ! -f $SITESPEED_BUDGET_FILE ]]; then
        echo "ERROR: Specified SITESPEED_BUDGET_FILE '$SITESPEED_BUDGET_FILE' does not exist."
        exit 1
    fi
fi

echo "Cleaning out old results if they exist"
rm -rf sitespeed-result
mkdir sitespeed-result

doGetCookie() {
    # Use the url and credential information to log in and create a file with the session cookie data
    ARGS="edx-sitespeed/edx_sitespeed/edx_sitespeed.py -e ${EDX_USER} -p ${EDX_PASS} -u ${TEST_URL}"
    if [[ $USE_BASIC_AUTH == "true" ]] ; then
        ARGS="${ARGS} --auth_user ${AUTH_USER} --auth_pass ${AUTH_PASS}"
    fi
    echo "Recording the session cookie for a logged-in user"
    echo "Using this command: python ${ARGS}"
    python ${ARGS}

}


doConstructArgs() {
    local RESULTS_FOLDER=$1


    ARGS="--requestHeaders cookie.json --suppressDomainFolder"
    ARGS="${ARGS} --outputFolderName ${RESULTS_FOLDER} --screenshot --storeJson"
    ARGS="${ARGS} -d 0 -n ${NUMBER_OF_TIMES} --connection ${CONNECTION} -v"


    # Only try to take the timings with an actual browser.
    # Note that the -b option is what uses the NUMBER_OF_TIMES
    # setting and it is also what does the HAR file capture.
    if [[ $SITESPEED_BROWSER != "headless" ]] ; then
        ARGS="${ARGS} -b ${SITESPEED_BROWSER}"
    fi

    if [[ $USE_BASIC_AUTH == "true" ]] ; then
        ARGS="${ARGS} --basicAuth ${AUTH_USER}:${AUTH_PASS}"
    fi

}

doConstructCMD() {
# This is the command with all the arguments defined as necessary.
CMD="sitespeed.io ${ARGS}"

# If we specify a browser other than "headless" (e.g. firefox)
# then we need to use xvfb to run the browser headlessly
if [[ $SITESPEED_BROWSER != "headless" ]] ; then
    CMD="xvfb-run $CMD"
fi

}

# Get cookie.json
doGetCookie

# Do all the pages first. (Because the one page may generate failures and kill the build.)
if [[ -f $TMP_URL_FILE ]] ; then
    if [[ ! -z $TMP_URL_FILE ]] ; then
        doConstructArgs allpages
        ARGS="${ARGS} -f ${TMP_URL_FILE}"
        doConstructCMD
        echo "Measuring client side performance with sitespeed. All pages (reporting purposes only.)"
        echo "Using this command: ${CMD} 2> sitespeed-result/all-stderr.log 1> sitespeed-result/all-stdout.log"
        ${CMD} 2> sitespeed-result/all-stderr.log 1> sitespeed-result/all-stdout.log
    fi
fi


# Just for the first page in the file
doConstructArgs firstpage
ARGS="${ARGS} -u ${TEST_URL}"
if [[ $SITESPEED_USE_BUDGET == "true" ]] ; then
    ARGS="${ARGS} --budget ${SITESPEED_BUDGET_FILE} --junit"
fi
doConstructCMD

echo "Measuring client side performance with sitespeed. First page."
if [[ ${CMD} =~ " --junit" ]] ; then
    # With --junit, sitespeed.io outputs the junit results to console.
    # Redirect them to a file instead so that a Jenkins plugin can interpret the results.
    echo "Using this command: ${CMD} 2> sitespeed-result/first-stderr.log 1> sitespeed-result/first-junit.xml"
    ${CMD} 2> sitespeed-result/first-stderr.log 1> sitespeed-result/first-junit.xml
else
    echo "Using this command: ${CMD} 2> sitespeed-result/first-stderr.log 1> sitespeed-result/first-stdout.log"
    ${CMD} 2> sitespeed-result/first-stderr.log 1> sitespeed-result/first-stdout.log
    # Write a placeholder result to the JUnit test result report so that Jenkins does not fail the build.
    cat > sitespeed-result/first-junit.xml <<END
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="sitespeed" tests="1" errors="0" failures="0" skip="0">
<testcase classname="sitespeed" name="placeholder" time="0.001"></testcase>
</testsuite>
END
fi

# Cleanup
rm -rf cookie.json
