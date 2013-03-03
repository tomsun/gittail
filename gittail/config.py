# The remote servers containing the repositories you want to watch
# GitTail will connect to this host using SSH and run "git log".
# You need to have key based SSH authentication set up for this to work.
"""
ssh_hosts = [
    {
        "host": "example.com",
        "repos": [
            # Path to the Git repositories
            # Construct the path so that `ls -d $repo_path` enumerates the repos
            # you want to watch.
            {
                "path: "/home/git/*/*.git",
            },
        ],
    },
]
"""


# Path to the local Git repositories you want to watch
# Construct the path so that `ls -d $repo_path` enumerates the repos.
"""
local_repo_paths = [
    "~/git/*",
]
"""


# How often GitTail opens a new SSH connection and gathers statistics
#
# poll_interval = 60


# The amount of simultaneous new commits required, to trigger
# digest notification instead of individual notifications.
#
# digest_threshold = 10   # (default: 10)


# Means of messaging that GitTail should attempt to use for each new event
# in addition to printing to the console
#
# use_growl = True        # OS X, Windows (default: if module exists)
# use_libnotify = True    # Linux (default: if module exists)
