#!/usr/bin/env python

""" Git plugin for GitHub integration
"""

import argparse
import os
from pprint import pprint

import git
import pygithub3

class GithubActor(object):
    """
    """

    CONFIG_NS       = 'hub'

    _current_repo   = None
    _current_user   = None
    _github         = None

    def __init__(self, output=None):
        self._current_repo = self._init_repo()
        creds = self._get_github_credentials(self._current_repo)
        self._current_user = creds[0]
        self._github = self._init_github(creds[0], creds[1], self._current_repo)
        if output is not None:
            self._output = output

    def _output(self, obj, *pargs, **kwargs):
        if issubclass(obj.__class__, basestring):
            print obj.format(*pargs, **kwargs)
        else:
            try:
                pprint(obj, indent=2)
            except Exception:
                print repr(obj)

    def _init_repo(self):
        try:
            repo = git.Repo(os.getcwd())
        except git.exc.InvalidGitRepositoryError:
            repo = None
        return repo

    def _init_github(self, username, password, repo=None):
        repo_name = self._get_repo_name(repo)
        return pygithub3.Github(login=username, password=password,
            user=username, repo=repo_name)

    def _get_repo_name(self, repo):
        if repo is not None:
            return os.path.basename(repo.working_tree_dir)
        else:
            return None

    def _get_github_credentials(self, repo=None):
        if repo is None:
            user_cfg_file = os.path.expanduser('~/.gitconfig')
            if os.path.exists(user_cfg_file):
                cfg = git.config.GitConfigParser(user_cfg_file)
            else:
                raise ValueError("""Can\'t find a gitconfig file for github login info.
                                    Set the login info with:
                                        git config --global --add {0}.username <username>
                                        git config --global --add {0}.password <password>
                                 """.format(self.CONFIG_NS))
        else:
            cfg = repo.config_reader()

        return (cfg.get_value(self.CONFIG_NS, 'username'),
            cfg.get_value(self.CONFIG_NS, 'password'))

    def repos_list(self, **kwargs):
        repos = self._github.repos.list(user=kwargs.get('user', self._current_user),
            type=kwargs.get('type', 'all')).all()
        padding = max(len(r.name) for r in repos)
        for repo in repos:
            fork_icon = 'V' if repo.fork else '|'
            self._output(' {fork_icon} {name: <{padding}} -- {description}',
                fork_icon=fork_icon, padding=padding, **vars(repo))

    def repos_create(self, **kwargs):
        new_repo = self._github.repos.create(kwargs, in_org=kwargs.get('in_org', None))
        self._output(new_repo)

    def repos_fork(self, **kwargs):
        pass

    def repos_addremote(self, **kwargs):
        pass

    def pr_list(self, **kwargs):
        kwargs['user'] = 'overviewer'
        pull_requests = self._github.pull_requests.list(
            user=kwargs.get('user', kwargs.get('user', self._current_user)),
            repo=kwargs.get('repo', self._get_repo_name(self._current_repo))).all()
        padding = max(len(pr.user['login']) for pr in pull_requests)
        for pr in pull_requests:
            commit_count = len(self._github.pull_requests.list_commits(pr.number,
                user=kwargs.get('user', kwargs.get('user', self._current_user)),
                repo=kwargs.get('repo', self._get_repo_name(self._current_repo))).all())
            self._output('#{number:0>4} {commit_count:0>2}c @{user[login]: <{padding}} {title} -- <{html_url}>',
                padding=padding, commit_count=commit_count, **vars(pr))

    def pr_merge(self, **kwargs):
        pass

def build_parser(actor):
    parser = argparse.ArgumentParser(description='git-hub - Do stuff with GitHub',
        prog='git-hub')
    parser.add_argument('--verbose', help='Display more output', action='store_true')
    sub_parsers = parser.add_subparsers(title='GitHub commands',
        dest='sub_command')

    #oh god wat
    command_verbs = dict((c, [v.split('_', 1)[1] for v in dir(actor) \
            if v.startswith(c+'_') and callable(getattr(actor, v))]) \
        for c in set(c.split('_')[0] for c in dir(actor) \
            if not c.startswith('_') and callable(getattr(actor, c))))

    parent_subparser = argparse.ArgumentParser(add_help=False)
    parent_subparser.add_argument('verb', metavar='VERB')
    for sub_command in command_verbs:
        sub_parser = sub_parsers.add_parser(sub_command)
        sub_parser.add_argument('verb', metavar='VERB', choices=command_verbs[sub_command])
    return parser

def handle_parsed(actor, parser_result):
    command_verb = parser_result.sub_command + '_' + parser_result.verb
    command = getattr(actor, command_verb)
    return command(**vars(parser_result))

def main():
    actor = GithubActor()
    parser = build_parser(actor)
    handle_parsed(actor, parser.parse_args())

if __name__ == '__main__':
    main()
