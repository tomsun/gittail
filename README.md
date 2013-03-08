GitTail
=======

A command-line utility written in Python that watches a set of Git repositories
and sends notifications via Growl or Libnotify when new commits are spotted.

GitTail can help emphasize the social aspect of coding. It can be a useful tool
for teams of developers in that it encourages awareness of and interaction
around code as it is being written, in an opt-in fashion per individual and per
given moment.

Git's distributed nature means you are not locked in to a single central
service. If somebody shares their Git repo with you, you can watch it with
GitTail.

GitTail can watch:

- Remote repositories accessible over SSH - provided that "git log"
  can be executed on the remote host.

- Local repositories - useful if you have local copies of the interesting repos
  which are somehow kept up to date, for example by a script that runs
  "git fetch" regularly or if a shared filesystem is mounted, which your
  colleagues push to.


INSTALLATION
------------

If you've downloaded the source repository, run "git submodule update --init"
to fetch the dependencies.

Alter config.py to suit your needs. Or create a custom config file and load it
via the -c option. Configure the path for at least one Git repository.

GitTail uses SSH to execute "git log" on a remote server to gather data.
Hence you need to set up key based SSH authentication for all SSH hosts you've
asked GitTail to watch, to avoid repeated password prompts.

Follow the platform specific instructions below.

Start the watchdog with "python gittail/gittail.py"


### OS X

Install Growl available at http://growl.info

Git is required for local repo support.

The bundled Growl bindings require Growl 2. For compatibility with older
versions of Growl, try installing these bindings
https://code.google.com/p/growl/source/browse/Bindings/python?name=maintenance-1.2


### Linux

GitTail attempts to use Libnotify by default,
via the Python module gi.repository.Notify.

Git is required for local repo support.


### Windows

To get notifications, install Growl for Windows.
http://code.google.com/p/growl-for-windows/

For remote repositories, GitTail attempts to execute the shell command "ssh".
For local repositories, GitTail needs a proper shell that supports conditionals,
loops, "ls" etc. The repo analysis is done using "git log".

This can be accomplished on Windows by running GitTail via Cygwin. Install the
corresponding Cygwin packages (OpenSSH, Git) depending on which GitTail features
you intend to use. If you don't have Python installed Cygwin can provide it too.
http://cygwin.org
