# -*- coding: utf-8 -*-

import subprocess
import time
from growl import Growl


"""
Watches a set of remote Git repositores and sends Growl notifications
when new commits are spotted.

Author: Tom Sundström
"""
class GitTail():
    def __init__(self, **kwargs):
        self.commits = {}
        self.commits_by_author = {}
        self.commits_by_committer = {}
        self.growler = Growl.GrowlNotifier(applicationName='GitTail', notifications=['commit'])
        self.growler.register()

        # Properties to extract when using git log
        # man git-log for details:
        self._git_log_commit_data = {
            'hash': '%H',
            'committer': '%cn',
            'author': '%an',
            'time': '%cr',
            'subject': '%s',
        }
        self._git_log_commit_delimiter = '|'

        try:
            self._config_value = kwargs["config"]
        except KeyError:
            self._config_value = {}


    """
    Read config values provided on initialization
    and allow programmatic default values
    """
    def _config(self, name, default=None):
        try:
            return self._config_value[name]
        except KeyError:
            if default == None:
                raise KeyError("GitTail configuration value '%s' is not set" % name)
            return default


    def notify(self, headline, message):
        self.growler.notify('commit', headline, message)

    def poll(self):
        first_run = (False, True)[len(self.commits) == 0]

        new_commits = []

        ssh_hosts = self._config("ssh_hosts")
        for host in ssh_hosts:
            for path in host["repo_paths"]:
                result = self.poll_ssh_host(host["host"], path)
                for commit in result:
                    new_commits.append(commit)

        if first_run:
            self.send_first_run_notification()
            return

        if len(new_commits) > 0:
            for commit in new_commits:
                self.send_commit_notification(commit)


    """
    Returns as string containing the git log command including all parameters
    required to produce a list of commits in the format that
    _parse_git_log_result() expects.
    """
    def _git_log_command(self):
        commit_format = self._git_log_commit_delimiter.join(self._git_log_commit_data.values())

        # Time period to watch
        since = '1 day ago'

        return 'git log --pretty=format:"commit=' + commit_format + '%n" --all --since="' + since + '"'


    def _repo_iteration_command(self, repo_path):
        return 'for repo in $( ls -d %s ) ; do if [ -d $repo ] ; then cd $repo ; echo "repo=$repo" ; %s ; fi ; done' % (repo_path, self._git_log_command())

    """
    Fetches commit info from a remote server using SSH and git log
    """
    def poll_ssh_host(self, host, repo_path):
        p = subprocess.Popen(
            [
                'ssh',
                host,
                self._repo_iteration_command(repo_path),
            ],
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE
        )
        result, error = p.communicate()
        return self._parse_git_log_result(result)


    """
    Parses response from git log
    """
    def _parse_git_log_result(self, result):
        new_commits = []
        current_repo = None
        for line in result.split("\n"):
            if line[0:5] == 'repo=':
                current_repo = line[5:]
                print "Checking repository %s" % current_repo
            elif line[0:7] == 'commit=':
                commit_parts = line[7:].split(self._git_log_commit_delimiter)
                commit_parts.reverse()
                commit = {}
                for id in self._git_log_commit_data.keys():
                    commit[id] = commit_parts.pop()
                commit['repo'] = current_repo
                print "Found commit %s" % str(commit)

                if not self.commits_by_committer.has_key(commit['committer']) or not self.commits_by_committer[commit['committer']].has_key(commit['hash']):
                    new_commits.append(commit)

                self.commits[commit['hash']] = commit
                if not self.commits_by_author.has_key(commit['author']):
                    self.commits_by_author[commit['author']] = {}
                self.commits_by_author[commit['author']][commit['hash']] = commit
                if not self.commits_by_committer.has_key(commit['committer']):
                    self.commits_by_committer[commit['committer']] = {}
                self.commits_by_committer[commit['committer']][commit['hash']] = commit

        return new_commits


    """
    Builds and sends notice message for a single commit
    """
    def send_commit_notification(self, commit):
        headline = "%s committed" % commit['committer']
        desc = "%s" % commit['repo']
        desc += "\n%s" % commit['subject']
        desc += "\n%s" % commit['time']
        if commit['author'] != commit['committer']:
            desc += "\nAuthor: %s" % commit['author']
        desc += "\n%s" % commit['hash']
        self.notify(headline, desc)


    """
    Builds and sends notice message for the first run
    """
    def send_first_run_notification(self):
        # Fist run, just summarize status
        headline = "Commit activity last 24 hours"
        if len(self.commits) == 0:
            self.notify(headline, "No activity")
        else:
            author_info = []
            for author in self.commits_by_author:
                commit_count = len(self.commits_by_author[author])
                author_info.append("%s %d %s" % (author, commit_count, ('commits', 'commit')[commit_count == 1]))
            self.notify(headline, "\n".join(author_info))


    def run(self):
        while True:
            self.poll()
            time.sleep(self._config("poll_interval", 60))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config')
    args = parser.parse_args()

    if args.config == None:
        # Use bundled config file
        import config as config_file
    else:
        # Use user specified config file
        import imp
        config_file = imp.load_source("config_file", args.config)

    gittail_config_dict = {}
    for k in config_file.__dict__:
        if k[0:2] != '__':
            gittail_config_dict[k] = config_file.__dict__[k]

    client = GitTail(config=gittail_config_dict)
    client.run()
