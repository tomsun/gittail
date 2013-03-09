# The remote servers containing the repositories you want to watch
# GitTail will connect to this host using SSH and run "git log".
# You need to have key based SSH authentication set up for this to work.
"""
ssh_hosts = [
    {
        "host": "example.com",
        # "user": "foo",
        "repos": [
            # Construct the path so that `ls -d $base_path/$pattern`
            # enumerates the repos you want to watch.
            {
                "base_path": "/home/git",
                "pattern": "*.git",
                # "gitweb_baseurl": "https://example.com",
            },
        ],
    },
]
"""


# Path to the local Git repositories you want to watch
# Construct the path so that `ls -d $repo_path` enumerates the repos.
"""
local_repos= [
    {
        "base_path": "~/git",
        "pattern": "*",
        # "github_paths": {
        #     "gittail": "tomsun/gittail",
        # },
    },
]
"""


# How often GitTail opens a new SSH connection and gathers statistics
#
# poll_interval = 60


# The amount of simultaneous new commits required, to trigger
# digest notification instead of individual notifications.
#
# digest_threshold = 10   # (default: 10)


# Growl configuration
#
# use_growl = True        # OS X, Windows (default: if module exists)


# Libnotify configuration
#
# use_libnotify = True    # Linux (default: if module exists)
"""
libnotify_note = {
    'timeout': 10000,
    'urgency': 0,

    'commit': {
        'urgency': 1,
    },
    'commit_digest': {
        'timeout': 15000,
    },
    'commit_digest_first_run': {
        'timeout': 5000,
    },
}
"""


# Message template settings
#
# use_templates = True    # (default: True)
# template_path = 'templates'

