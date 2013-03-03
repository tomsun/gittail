# -*- coding: utf-8 -*-

import subprocess
import time


"""
Watches a set of remote Git repositores and sends Growl notifications
when new commits are spotted.

Author: Tom Sundström
"""
class GitTail():
    def __init__(self, **kwargs):
        self.first_run = True
        self.commits = {}
        self.commits_by_author = {}
        self.commits_by_committer = {}

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

        self.verbosity = self._config("verbosity", 0)
        if self._config("quiet", 0) == 1: self.verbosity = -1

        if self._config("use_libnotify", True):
            try:
                from gi.repository import Notify as libnotify
                self.libnotify = libnotify
                self.libnotify.init("GitTail")
            except ImportError, e:
                self.log("Failed to import gi.repository.Notify")
                self._config_value["use_libnotify"] = False

        if self._config("use_growl", True):
            try:
                from growl import Growl
                self.growler = Growl.GrowlNotifier(applicationName='GitTail', notifications=['commit'])
                self.growler.register()
            except ImportError, e:
                self.log("Failed to load Growl bindings")
                self._config_value["use_growl"] = False


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
        self.log("\n- %s: %s\n" % (headline, message))

        if self._config("use_growl", True):
            self.growler.notify('commit', headline, message)

        if self._config("use_libnotify", True):
            Note=self.libnotify.Notification.new(headline, message, "dialog-information")
            Note.show()


    """
    Logging of less important messages
    Might be presented in the console depending on the verbosity level,
    but are not sent to the notification system.
    """
    def log(self, message, min_verbosity = 0):
        if self.verbosity >= min_verbosity:
            print message


    def poll(self):
        new_commits = []

        ssh_hosts = self._config("ssh_hosts", [])
        for host in ssh_hosts:
            self.log("Checking SSH host '%s'" % host["host"], 1)
            for path in host["repo_paths"]:
                self.log("Checking repo pattern '%s'" % path, 2)
                result = self.poll_ssh_host(host, path)
                for commit in result:
                    new_commits.append(commit)

        local_repos = self._config("local_repo_paths", [])
        for path in local_repos:
            self.log("Checking local repo pattern '%s'" % path, 1)
            result = self.poll_local_path(path)
            for commit in result:
                new_commits.append(commit)

        if len(ssh_hosts) == 0 and len(local_repos) == 0:
            self.log("No repos configured")
            return False

        if self.first_run:
            self.send_first_run_notification()
            self.first_run = False
            return True

        if len(new_commits) > 0:
            for commit in new_commits:
                self.send_commit_notification(commit)

        return True


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
                host["host"],
                self._repo_iteration_command(repo_path),
            ],
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE
        )
        result, error = p.communicate()
        if error != '':
            self.log("subprocess error: '%s'" % error)
        return self._parse_git_log_result(result)


    """
    Fetches commit info from a local path using git log
    """
    def poll_local_path(self, repo_path):
        try:
            result = subprocess.check_output(self._repo_iteration_command(repo_path), shell=True)
        except subprocess.CalledProcessError, e:
            self.log("subprocess error: '%s'" % e)
            return
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
                self.log("Checking repository %s" % current_repo, 2)
            elif line[0:7] == 'commit=':
                commit_parts = line[7:].split(self._git_log_commit_delimiter)
                commit_parts.reverse()
                commit = {}
                for id in self._git_log_commit_data.keys():
                    commit[id] = commit_parts.pop()
                commit['repo'] = current_repo

                if not self.commits_by_committer.has_key(commit['committer']) or not self.commits_by_committer[commit['committer']].has_key(commit['hash']):
                    new_commits.append(commit)
                    self.log("Found new commit %s" % str(commit), 3)
                else:
                    self.log("Found previously seen commit %s" % str(commit), 4)

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
        while self.poll():
            interval = self._config("poll_interval", 60)
            self.log("Sleeping %d seconds" % interval, 1)
            time.sleep(interval)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config')
    parser.add_argument('-v', '--verbose', action='count')
    parser.add_argument('-q', '--quiet', action='count')
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

    if args.verbose != None:
        gittail_config_dict["verbosity"] = args.verbose
    if args.quiet != None:
        gittail_config_dict["quiet"] = args.quiet

    client = GitTail(config=gittail_config_dict)
    client.run()
