"""
Get build info
"""

import requests

BASE_URL = 'https://api.travis-ci.org/'


def get_repos(org):
    """
    Returns list of active repos in a given org.
    """

    repo_list = []
    req = requests.get(BASE_URL + 'v3/owner/{org}/repos?active=true'.format(org=org))
    req_json = req.json()
    for i in req_json['repositories']:
        repo_list.append(i['name'])

    return repo_list


def get_builds(org, repo):
    """
    Returns list of builds for a given repo slug
    """

    repo_slug = '{org}/{repo}'.format(org=org, repo=repo)
    req = requests.get(BASE_URL + 'repos/{repo_slug}/builds'.format(repo_slug=repo_slug))
    build_list = req.json()
    return build_list


@property
def state_of_build(build_item):
    """
    input: build_list[i]
    """
    return build_item['state']

@property
def build_id(build_item):

    return build_item['id']


def get_jobs(build_id):
    """
    Get the jobs for a build
    return: list of dicts
    """

    req = requests.get(BASE_URL + 'v3/build/{build_id}/jobs'.format(build_id=build_id))
    return req['jobs']

@property
def job_state(job_dict):
    """
    possible states:
    * received
    * queued
    * created
    * is there a started?
    """

    return job_dict['state']

# repos = get_repos('edx')
# builds = []
# for i in repos:
#     builds.append(get_builds('edx', i))
#
# count = 0
#
# for i in builds:
#     for j in i:
#         if j['state'] != 'finished':
#             count += 1
#             print j['state']
#
# print count

repos = get_repos('edx')
builds = []
main_count = 0
main_started_count = 0

for rep in repos:
    total_count = 0
    started_count = 0
    repo_builds = []
    repo_builds.append(get_builds('edx', rep))
    print "--->" + rep

    for i in repo_builds:
        for j in i:
            if j['state'] != 'finished':
                total_count += 1
                # print j['state']
                if j['state'] == 'started':
                    started_count += 1

    main_count += total_count
    main_started_count += started_count
    print "total: " + str(total_count), "started: " + str(started_count)

print '--------'
print "overall_total=" + str(main_count)
print "overall_started=" + str(main_started_count)
print "overall_queued=" + str(main_count - main_started_count)

