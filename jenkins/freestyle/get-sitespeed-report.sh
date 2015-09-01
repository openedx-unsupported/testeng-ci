#!/bin/bash
set -e

# Sitespeed job script
# Assumes the following environment variables are set
#
# TEST_URL
# EDX_USER
# EDX_PASS
# USE_BASIC_AUTH
# AUTH_USER (optional, required if USE_BASIC_AUTH)
# AUTH_PASS (optional, required if USE_BASIC_AUTH)
# NUMBER_OF_TIMES
# CONNECTION
# SITESPEED_BROWSER

: ${TEST_URL:?"The TEST_URL environment variable must be set."}
: ${EDX_USER:?"The EDX_USER environment variable must be set."}
: ${EDX_PASS:?"The EDX_PASS environment variable must be set."}
: ${USE_BASIC_AUTH:?"The USE_BASIC_AUTH environment variable must be set."}
: ${NUMBER_OF_TIMES:?"The NUMBER_OF_TIMES environment variable must be set."}
: ${CONNECTION:?"The CONNECTION environment variable must be set."}
: ${SITESPEED_BROWSER:?"The SITESPEED_BROWSER environment variable must be set."}

echo "Cleaning out old results if they exist"
rm -rf sitespeed-result
mkdir sitespeed-result

# create a file with the session credential cookie
ARGS="edx-sitespeed/edx_sitespeed/edx_sitespeed.py -e ${EDX_USER} -p ${EDX_PASS} -u ${TEST_URL}"
if [ -n "$USE_BASIC_AUTH" ] ;
    then ARGS="${ARGS} --auth_user ${AUTH_USER} --auth_pass ${AUTH_PASS}"
fi
echo "Recording the session cookie for a logged-in user"
echo "Using this command: python ${ARGS}"
python ${ARGS}

# use firefox as a browser with browsertime/browsermobproxy to get waterfalls etc
ARGS="-u ${TEST_URL} --requestHeaders cookie.json --junit --suppressDomainFolder --outputFolderName results --screenshot --storeJson"
ARGS="${ARGS} -b ${SITESPEED_BROWSER} -d 0 -n ${NUMBER_OF_TIMES} --connection ${CONNECTION}"
if [ -n "$USE_BASIC_AUTH" ] ;
    then ARGS="${ARGS} --basicAuth ${AUTH_USER}:${AUTH_PASS}"
fi

# if we are using the --b option with sitespeed,
# then we need to use xvfb to run the browser headlessly
# otherwise we would just call sitespeed.io directly
echo "Measuring client side performance with sitespeed"
echo "Using this command: xvfb-run sitespeed.io ${ARGS} > sitespeed-result/junit.xml"
xvfb-run sitespeed.io ${ARGS} > sitespeed-result/junit.xml

# cleanup
rm -rf cookie.json
