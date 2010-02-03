# -*- coding: utf-8 -*-

import subprocess
import time
from growl import Growl
import config


"""
Watches a set of remote Git repositores and sends Growl notifications
when new commits are spotted.

Author: Tom Sundström
"""
class GitTail():
    def __init__(self):
        self.commits = {}
        self.growler = Growl.GrowlNotifier(applicationName='GitTail', notifications=['commit'])
        self.growler.register()

    def notify(self, headline, message):
        self.growler.notify('commit', headline, message)

    def fetch(self):
        # Commit format
        # man git-log for details:
        commit_data = {
            'hash': '%H',
            'committer': '%cn',
            'author': '%an',
            'time': '%cr',
            'subject': '%s',
        }
        commit_delimiter = '|'
        commit_keys = commit_data.keys()
        commit_format = commit_delimiter.join(commit_data.values())

        # Time period to watch
        since = '1 day ago'

        # Fetch commit info using SSH and Git on remote server
        p = subprocess.Popen(
            [
                'ssh',
                config.git_host,
                'for repo in $( ls -d ' + config.repo_path + ' ) ; do if [ -d $repo ] ; then cd $repo ; echo "repo=$repo" ; git log --pretty=format:"commit=' + commit_format + '%n" --all --since="' + since + '" ; fi ; done',
            ],
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE
        )
        result, error = p.communicate()

        current_repo = None
        for line in result.split("\n"):
            if line[0:5] == 'repo=':
                current_repo = line[5:]
                print "Checking repository %s" % current_repo
            elif line[0:7] == 'commit=':
                commit_parts = line[7:].split(commit_delimiter)
                commit_parts.reverse()
                commit = {}
                for id in commit_keys:
                    commit[id] = commit_parts.pop()
                print "Found commit %s" % str(commit)
                self.commits[commit['hash']] = commit


    def run(self):
        while True:
            self.fetch()
            time.sleep(config.poll_interval)


if __name__ == "__main__":
    client = GitTail()
    client.run()
