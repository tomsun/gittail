# The remote servers containing the repositories you want to watch
# GitTail will connect to this host using SSH and run "git log".
# You need to have key based SSH authentication set up for this to work.
"""
ssh_hosts = [
    {
        "host": "example.com",
        "repo_paths": [
            # Path to the Git repositories
            # Construct the path so that `ls -d $repo_path` enumerates the repos
            # you want to watch.
            "/home/git/*/*.git",
        ],
    },
]
"""


# How often GitTail opens a new SSH connection and gathers statistics
#
# poll_interval = 60
