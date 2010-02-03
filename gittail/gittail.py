# -*- coding: utf-8 -*-

import subprocess
from growl import Growl
import config


"""
Watches a set of remote Git repositores and sends Growl notifications
when new commits are spotted.

Author: Tom Sundström
"""
class GitTail():
    def __init__(self):
        self.growler = Growl.GrowlNotifier(applicationName='GitTail', notifications=['commit'])
        self.growler.register()

    def notify(self, headline, message):
        self.growler.notify('commit', headline, message)

    def fetch(self):
        # Commit format
        # man git-log for details:
        commit_format = '%H|%cn|%an|%cr|%s'

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
        print result
        print error

    def run(self):
        self.fetch()


if __name__ == "__main__":
    client = GitTail()
    client.run()
