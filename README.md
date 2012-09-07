git-hub
=======

Git plugin for GitHub integration. Not written/provided/endorsed/supported/etc
by GitHub in any way.

I was tired of having to open up the GitHub website just to create a new repo,
or get the clone URL so I wrote a plugin to do it all from git.

## Usage

Run it like any other ``git`` command:
~~~~
$ git hub -h
usage: git-hub [-h] [--verbose] [--user USER] [--repo REPO] {pr,repos} ...

git-hub - Do stuff with GitHub

optional arguments:
  -h, --help   show this help message and exit
  --verbose    Display more output
  --user USER  Override target username
  --repo REPO  Override target repo name

GitHub commands:
  {pr,repos}

# list your repos
$ git hub repos list | head -3
 | 4chan-utils               -- Some useful scripts for 4chan and a python module.
 V apache-mod-markdown       -- Markdown filter module for Apache HTTPD Server
 V appserver-in-php          -- Generic HTTP applications approach for PHP5.3+ (inspired by Rack and WSGI)

# list someone else's repos
$ git hub --user torvalds repos list
 | linux      -- Linux kernel source tree
 | subsurface -- Rough divelog in C and Gtk

# fork a repo
$ git hub --user overviewer --repo Minecraft-Overviewer repos fork

# then clone it
$ git hub --repo Minecraft-Overviewer repos clone
~~~~

It's important to note that placement of the ``--user`` and ``--repo`` options is
significant, they must come after the ``hub`` part, and before any subcommands (like
``repos`` or ``pr``).

## Configuration

The username defaults to your GitHub user, and the repo will default to the repo
you're currently in (if you're in one). GitHub login info can be configured like
any other git configuration:
~~~~
$ git config --global --add hub.username <your username>
$ git config --global --add hub.password <your password>
~~~~

## Installation
Because of the requirements, this isn't super easy. At some point I intend to
fix this but for now you'll have to make due.

The basic outline is:
  * Clone the repo to somewhere
  * Install the requirements in a virtualenv or at the system level
  * Change the shebang line in ``git-hub.py`` to use the python from the virtualenv
    (if you used one) or the system python (otherwise other virtualenvs will mess
    things up)
  * Either symlink to ``git-hub.py`` from somewhere in your path (to use the command
    by itself, which works fine) or from ``/usr/libexec/git-core/git-hub`` to add to
    ``git``

## Requirements
  * Python 2.7+ (lower versions may work but the ``argparse`` module will need
    to be installed)
  * [pygithub3](https://github.com/copitux/python-github3)
  * [GitPython](https://github.com/gitpython-developers/GitPython)
  * [requests](https://github.com/kennethreitz/requests) < 0.14 (pygithub3 does
    not work with 0.14+)

https://gist.github.com/3649930
