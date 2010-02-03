# -*- coding: utf-8 -*-

from growl import Growl


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

    def run(self):
        self.notify("Hello", "World!")


if __name__ == "__main__":
    client = GitTail()
    client.run()
