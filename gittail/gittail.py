# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 Tom Sundström (office@tomsun.ax)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


"""
GitTail

A command-line utility written in Python that watches a set of Git repositories
and sends notifications via Growl or Libnotify when new commits are spotted.
"""

import os
import sys
import subprocess
import time

import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)

# Make bundled Git submodules includable
lib_path = "%s/../lib" % os.path.dirname(__file__)
if os.path.isdir(lib_path):
    for path in os.listdir(lib_path):
        submodule_path = "%s/%s" % (lib_path, path)
        if os.path.isdir(submodule_path):
            sys.path.append(submodule_path)


class GitTail():
    def __init__(self, **kwargs):
        self.first_run = True
        self.commits = {}

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

        if self._config("use_libnotify", -1) in [True, -1]:
            try:
                from gi.repository import Notify as libnotify
                self.libnotify = libnotify
                self.libnotify.init("GitTail")
            except ImportError, e:
                msg = "Failed to import gi.repository.Notify"
                if self._config("use_libnotify", -1) == True:
                    raise ImportError(msg)
                self.log(msg)
                self._config_value["use_libnotify"] = False

        if self._config("use_growl", -1) in [True, -1]:
            GrowlNotifier = None
            try:
                from growl import Growl
                GrowlNotifier = Growl.GrowlNotifier
            except ImportError, e:
                try:
                    import gntp.notifier
                    GrowlNotifier = gntp.notifier.GrowlNotifier
                except ImportError, e:
                    msg = "Failed to load Growl bindings"
                    if self._config("use_growl", -1) == True:
                        raise ImportError(msg)
                    self.log(msg)
                    self._config_value["use_growl"] = False

            if GrowlNotifier != None:
                self.growler = GrowlNotifier(
                    applicationName='GitTail',
                    notifications=['commit']
                )
                try:
                    self.growler.register()
                except gntp.errors.NetworkError, e:
                    self.log("gntp.errors.NetworkError: Growl not started?")
                    if self._config("use_growl", -1) == True:
                        raise e

        if self._config("use_templates", True):
            try:
                from jinja2 import Environment, FileSystemLoader
                import jinja2.exceptions as jinja2_exceptions
                self.jinja2_exceptions = jinja2_exceptions
                self.jinja2_default_templates = Environment(
                    loader=FileSystemLoader(
                        "%s/templates/jinja2" % os.path.dirname(__file__)),
                    trim_blocks=True)
                custom_template_path = self._config("template_path", False)
                if custom_template_path:
                    self.jinja2_custom_templates = Environment(
                        loader=FileSystemLoader(
                            "%s/jinja2" % custom_template_path),
                        trim_blocks=True)
            except ImportError:
                self.log("Failed to import jinja2 - using default messages")
                self._config_value["use_templates"] = False


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


    """
    Format and send messages to console and to the supported notification
    mechanisms
    """
    def notify(self, message_type, data):
        console_message = self._render_message(
            message_type, data, 'console')
        self.log(console_message['message'])

        if self._config("use_growl", True):
            growl_message = self._render_message(
                message_type, data, 'growl')
            title = growl_message['title']
            text = growl_message['text']
            icon = None
            sticky = False
            priority = None
            if growl_message.has_key('callback'):
                callback = growl_message['callback']
            else:
                callback = None
            try:
                try:
                    self.growler.notify('commit', title, text, icon, sticky, priority, callback)
                except TypeError:
                    # Support older bindings
                    self.growler.notify('commit', title, text, icon, sticky, priority)
            except Exception, e:
                self.log("Exception when calling growler.notify: Growl not started?")
                if self._config("use_growl", -1) == True:
                    raise e

        if self._config("use_libnotify", True):
            try:
                note_config = self._config('libnotify_note')
            except KeyError:
                note_config = {}
            try:
                for key in note_config[message_type]:
                    note_config[key] = note_config[message_type][key]
            except KeyError:
                pass

            libnotify_message = self._render_message(
                message_type, data, 'libnotify')
            Note=self.libnotify.Notification.new(
                libnotify_message['summary'],
                libnotify_message['body'],
                'dialog-information')

            if note_config.has_key('timeout'):
                Note.set_timeout(note_config['timeout'])

            if note_config.has_key('urgency'):
                Note.set_urgency(note_config['urgency'])

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
            for repo in host["repos"]:
                self.log("Checking path '%s' for pattern '%s'" % (repo["base_path"], repo["pattern"]), 2)
                result = self.poll_ssh_host(host, repo)
                for commit in result:
                    new_commits.append(commit)

        local_repos = self._config("local_repos", [])
        for repo in local_repos:
            self.log("Checking local path '%s' for pattern '%s'" % (repo["base_path"], repo["pattern"]), 2)
            result = self.poll_local_repo(repo)
            for commit in result:
                new_commits.append(commit)

        if len(ssh_hosts) == 0 and len(local_repos) == 0:
            self.log("No repos configured")
            return False

        if self.first_run:
            self.notify('commit_digest_first_run', {'commits': self.commits.values()})
            self.first_run = False
            return True

        if self._config("digest_threshold", 10) != 0:
            if len(new_commits) >= self._config("digest_threshold", 10):
                self.notify('commit_digest', {'commits': new_commits})
                return True

        if len(new_commits) > 0:
            for commit in new_commits:
                self.notify('commit', {'commit': commit})

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


    def _repo_iteration_command(self, repo):
        cmd = []

        if repo.has_key('base_path'):
            # list repos relative to base path
            cmd.append('cd %s' % repo['base_path'])

            # get absolute version of base_path
            cmd.append('base_path=`pwd`')

        # repo_path exands to a list of repos
        cmd.append('for repo in $( ls -d %s )' % repo['pattern'])

        # a valid repo is a directory
        # that either has the suffix ".git" (bare repo)
        # or contains a directory named ".git"
        cmd.append('do if [[ -d $repo && ( ${repo##*.} == "git" || -d $repo/.git ) ]]')

        # cd to root of repo for the benefit of git log
        cmd.append('then cd $repo')

        # add hint for _git_log_parse_result()
        cmd.append('echo "repo=$repo"')

        # add list of recent commits
        cmd.append(self._git_log_command())

        if repo.has_key('base_path'):
            # cd back to base path before handling next repo
            cmd.append('cd $base_path')

        cmd.append('fi')
        cmd.append('done')

        return "/bin/bash -c '%s'" % " ; ".join(cmd).replace("'", "\\\'")


    """
    Fetches commit info from a remote server using SSH and git log
    """
    def poll_ssh_host(self, host, repo):
        env = os.environ
        env['PYTHONIOENCODING'] = 'utf-8'

        args = ["ssh"]

        try:
            args.append("%s@%s" % (host["user"], host["host"]))
        except KeyError:
            args.append(host["host"])

        try:
            args.append("-p %d" % host["port"])
        except KeyError:
            pass

        args.append(self._repo_iteration_command(repo))

        p = subprocess.Popen(
            args,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            env=env
        )
        result, error = p.communicate()
        result = result.decode('utf-8')
        error = error.decode('utf-8')
        if error != '':
            self.log("subprocess error: '%s'" % error)
        return self._parse_git_log_result(result,
            **{"host": host, "repo": repo})


    """
    Fetches commit info from a local path using git log
    """
    def poll_local_repo(self, repo):
        try:
            env = os.environ
            env['PYTHONIOENCODING'] = 'utf-8'
            result = subprocess.check_output(
                self._repo_iteration_command(repo), shell=True, env=env)
        except subprocess.CalledProcessError, e:
            self.log("subprocess error: '%s'" % e)
            return
        result = result.decode('utf-8')
        return self._parse_git_log_result(result, **{"repo": repo})


    """
    Parses response from git log
    """
    def _parse_git_log_result(self, result, **kwargs):
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
                try:
                    gitweb_baseurl = kwargs['repo']['gitweb_baseurl']
                    commit['url'] = "%s?p=%s;a=commitdiff;h=%s" % (
                        gitweb_baseurl, current_repo, commit['hash'])
                except KeyError:
                    pass

                if not commit.has_key('url'):
                    try:
                        github_path = kwargs['repo']['github_paths'][current_repo]
                        commit['url'] = "https://github.com/%s/commit/%s" % (
                            github_path, commit['hash'])
                    except KeyError:
                        pass

                if not self.commits.has_key(commit['hash']):
                    new_commits.append(commit)
                    self.log("Found new commit %s" % str(commit), 3)
                else:
                    self.log("Found previously seen commit %s" % str(commit), 4)

                self.commits[commit['hash']] = commit

        new_commits.reverse()

        return new_commits


    def _render_template(self, template_path, data, default_value = None):
        data['default_value'] = default_value

        if not self._config("use_templates", True):
            return default_value

        try:
            template = self.jinja2_custom_templates.get_template(template_path)
            return template.render(**data)
        except (AttributeError, self.jinja2_exceptions.TemplateNotFound), e:
            try:
                template = self.jinja2_default_templates.get_template(template_path)
                return template.render(**data)
            except self.jinja2_exceptions.TemplateNotFound, e:
                if default_value:
                    return default_value
                raise e


    def _render_message(self, message_type, data, target):
        message = {}
        data['timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")
        data['indent_ts'] = "".join([" " for x in range(0,len(data['timestamp']))])

        """
        notification for a single commit
        """
        if message_type == 'commit':
            commit = data['commit']

            data['title'] = "%s committed" % commit['committer']

            default_body = []
            default_body.append(commit['repo'])
            default_body.append(commit['subject'])
            default_body.append(commit['time'])
            if commit['author'] != commit['committer']:
                default_body.append("Author: %s" % commit['author'])
            default_body.append(commit['hash'])

            if target == 'console':
                if commit.has_key('url'):
                    default_body.append(commit['url'])
                message['message'] = self._render_template(
                    'console/commit/message.txt',
                    data,
                    "\n%s %s\n%s\n" % (
                        data['timestamp'],
                        data['title'],
                        "\n".join(default_body)))

            elif target == 'growl':
                message['title'] = self._render_template(
                    'growl/commit/title.txt', data, data['title'])

                message['text'] = self._render_template(
                    'growl/commit/text.txt', data, "\n".join(default_body))

                if commit.has_key('url'):
                    message['callback'] = commit['url']

            elif target == 'libnotify':
                message['summary'] = self._render_template(
                    'libnotify/commit/summary.txt', data, data['title'])

                default_body = "\n".join(default_body)
                if commit.has_key('url'):
                    default_body = '<a href="%s">%s</a>' % (
                        commit['url'], default_body)

                message['body'] = self._render_template(
                    'libnotify/commit/body.html', data, default_body)


        """
        digest notification for multiple commits

        the threshold for when digest notification is used rather than
        individual commit notifiactions, can be set in config (default: 10)
        """
        if message_type == 'commit_digest':
            commits = data['commits']

            if not data.has_key('title'):
                data['title'] = 'Commit activity recently'

            default_body = []
            if len(commits) == 0:
                default_body.append('No activity')
            else:
                commits_per_author = {}
                for commit in commits:
                    try:
                        commits_per_author[commit["author"]] += 1
                    except KeyError:
                        commits_per_author[commit["author"]] = 1
                for author in commits_per_author:
                    default_body.append("%s %d %s" % (author, commits_per_author[author],
                        ('commits', 'commit')[commits_per_author[author] == 1]))
                data['commits_per_author'] = commits_per_author

            if target == 'console':
                message['message'] = self._render_template(
                    'console/commit_digest/message.txt',
                    data,
                    "\n%s %s\n%s\n" % (
                        data['timestamp'],
                        data['title'],
                        "\n".join(default_body)))

            elif target == 'growl':
                message['title'] = self._render_template(
                    'growl/commit_digest/title.txt',
                    data,
                    data['title'])

                message['text'] = self._render_template(
                    'growl/commit_digest/text.txt',
                    data,
                    "\n".join(default_body))

            elif target == 'libnotify':
                message['summary'] = self._render_template(
                    'libnotify/commit_digest/summary.txt',
                    data,
                    data['title'])

                message['body'] = self._render_template(
                    'libnotify/commit_digest/body.html',
                    data,
                    "\n".join(default_body))

        """"
        notification with results of the first pass after starting GitTail
        """
        if message_type == 'commit_digest_first_run':
            data['title'] = 'Commit activity last 24 hours'
            message = self._render_message('commit_digest', data, target)

        return message


    def run(self):
        while self.poll():
            interval = self._config("poll_interval", 60)
            self.log("Sleeping %d seconds" % interval, 1)
            time.sleep(interval)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="""A command-line utility written in Python that watches
        a set of Git repositories and sends notifications via Growl or Libnotify
        when new commits are spotted."""
    )
    parser.add_argument('-c', '--config',
        help='use a custom configuration file')
    parser.add_argument('-t', '--template',
        help='use a custom template directory')
    parser.add_argument('-v', '--verbose', action='count',
        help="""set to a value between 1 and 4 to increase the amount of
                information printed to the console""")
    parser.add_argument('-q', '--quiet', action='count',
        help='suppress non-error console messages')
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

    if args.template != None:
        gittail_config_dict["use_templates"] = True
        gittail_config_dict["template_path"] = args.template

    if args.verbose != None:
        gittail_config_dict["verbosity"] = args.verbose
    if args.quiet != None:
        gittail_config_dict["quiet"] = args.quiet

    client = GitTail(config=gittail_config_dict)
    client.run()


if __name__ == "__main__":
    main()
