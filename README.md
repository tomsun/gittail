GitTail
=======

A command-line utility written in Python that watches a set of Git repositories
and sends notifications via Growl or Libnotify when new commits are spotted.


INSTALLATION
------------

If you've downloaded the source repository, run "git submodule update --init"
to fetch the dependencies.

GitTail uses SSH to execute "git log" on a remote server to gather data.
Hence you need to set up key based SSH authentication to avoid password prompts.

Alter config.py to suit your needs. Configure the path for at least one Git
repository.

Follow the platform specific instructions below.

Start the watchdog with "python gittail/gittail.py"


### OS X

Install Growl available at http://growl.info

Git is also required.

The bundled Growl bindings require Growl 2. For compatibility with older
versions of Growl, try installing these bindings
https://code.google.com/p/growl/source/browse/Bindings/python?name=maintenance-1.2


### Linux

GitTail attempts to use Libnotify by default,
via the Python module gi.repository.Notify.

Git is also required.


### Windows

Install Growl for Windows available at http://www.growlforwindows.com

For remote repositories, GitTail attempts to execute the shell command "ssh".
For local repositories, GitTail needs a proper shell that supports conditionals,
loops, "ls" etc. The repo analysis is done using "git log".

This can be accomplished on Windows by running GitTail via Cygwin. Install the
corresponding Cygwin packages (OpenSSH, Git) depending on which GitTail features
you intend to use. If you don't have Python installed Cygwin can provide it too.
http://cygwin.org
