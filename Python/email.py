#!/usr/bin/env python
#---------------------------------------------------------------------
# Tool Generates iso build & bundle summary for Jenkins email
# Requires dependency for pyrpm and tabulate module
#---------------------------------------------------------------------

import argparse
import collections
import fnmatch
import json
import os
import re
import requests
import sys
from datetime import datetime
from pyrpm.rpm import RPM
from pyrpm import rpmdefs
from pytz import timezone
from sh import git
from tabulate import tabulate

def flatten(d, parent_key='', sep='__'):
    # Pulling the build summary from the manifest.json
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.dirname(os.path.join(root, name)))
    return result

def OAuth():
    with open('./.git-api-token.txt', 'r') as t:
        head = re.search(': (.*)', t.read()).group(1)
    return head

def commits(name, sha, head, branch):
    # Fetching commits by using SHA1
    print ("\n%s : " % name.upper())
    print ("    BRANCH    : %s" % branch)

    # Requests the git api to fetch the commit history basing on reponame and sha1
    token = {'Authorization': 'token '+ head}
    sm_url = git('config', '--file', '.gitmodules', '--get', 'submodule.' + name + '.url')
    sm_url = str(sm_url).strip()
    repo_name = sm_url.split('/')[-1].split('.')[0]
    url = "https://github.com/repos/code-Z/" + repo_name + "/commits/"
    wjdata = requests.get(url+sha, headers=token).json()
    abrev_sha = wjdata['sha'][:7]
    commit_sha_link = '<a href="https://github.com/code-Z/' + repo_name + '/tree/' + abrev_sha + '">' + abrev_sha + '</a>'
    print ("    SHA1      : %s" % commit_sha_link)
    print ("    EMAIL     : %s" % wjdata['commit']['author']['email'])

    # Converting the commit date timezone from UTC to PDT
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    date_str = wjdata['commit']['author']['date']
    datetime_obj = datetime.strptime(date_str, fmt)
    datetime_obj_utc = datetime_obj.replace(tzinfo=timezone('UTC'))
    now_pacific = datetime_obj_utc.astimezone(timezone('US/Pacific'))
    date_local = now_pacific.strftime(fmt)
    print ("    DATE      : %s" % date_local)

    # utf-8 is used as python doesn't encode unicode characters in message properly
    print ("    MESSAGE   : %s" % (wjdata['commit']['message'].encode('utf-8')).replace('\n', '\n                '))

def rpm_info(list):
    # Retrives the rpm bundle details 
    x = []
    y = ''
    for filepath in list:
        if filepath != y and filepath != '':
            y = filepath
            for f in os.listdir(filepath):
                if f.endswith('.rpm'):
                    file_loc = filepath + "/" + f
                    rpm = RPM(file(file_loc))
                    NAM = rpm[rpmdefs.RPMTAG_NAME]
                    VER = rpm[rpmdefs.RPMTAG_VERSION]
                    REL = rpm[rpmdefs.RPMTAG_RELEASE]
                    SHA = re.search('- \((.*)\)', rpm[rpmdefs.RPMTAG_DESCRIPTION]).group(1)
                    x.append([NAM, VER, REL, SHA])
    return x

def comp_list(data, name):
    list = []
    for comp, v in data.items():
        if comp.find(name) != -1 and comp.find('_info') == -1:
            k1 = comp.replace('Manifest__bundles__', '')
            k1 = k1.replace('checkouts__', '')
            k1 = k1.replace('__' + name, '')
            if k1.find('__') != -1:
                k1 = re.search('__(.*)', k1).group(1)
            list.append((k1, v))
    return list

def data_manifest(jsondir, token):
    # Reads the manifest.json and pull in the build data
    y = ''
    list_sha = []
    list_branch = []
    for jsonpath in jsondir:
        if jsonpath != y and jsonpath != '':
            y = jsonpath
            for f in os.listdir(jsonpath):
                if f.startswith('release'):
                    file_loc = jsonpath + "/" + f
                    with open(file_loc) as f:
                        data = json.load(f)
                    data = flatten(data)
                    list_sha = comp_list(data, 'checkout_sha')
                    list_branch = comp_list(data, 'checkout_branch')

    dict_sha = dict(list_sha)
    dict_branch = dict(list_branch)
    for comp, sha in dict_sha.items():
        commits(comp, sha, token, dict_branch[comp])

def main():
    data = []
    print "\nBUNDLE SUMMARY\n"
    dirlist = []
    headers = ['NAME', 'VERSION', 'RELEASE', 'COMMIT SHA']
    # Finds all rpm bundles in the release iso
    dirlist = find('*.rpm', './iso')

    x = rpm_info(dirlist)

    # creates table with the list of contents in iso
    print tabulate(x, headers, tablefmt="grid", numalign="right")

    print "\n\nSUBMODULE COMMITS :\n"
    # Fetching the SHA1 from Manifest.json
    git_token = OAuth()
    jsondir = []
    jsondir = find('manifest.json', './iso')
    data_manifest(jsondir, git_token)

main()
