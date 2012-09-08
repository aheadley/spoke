#!/usr/bin/env python

""" Git plugin for GitHub integration
"""

import argparse
import os
from pprint import pprint
import functools
import inspect

import git
import pygithub3

def guess_type(obj):
    ok_types = [int, str, bool]
    obj_type = type(obj)
    if obj_type in ok_types:
        return obj_type
    else:
        if obj_type == list or obj_type == tuple:
            if len(obj):
                obj_e_type = type(obj[0])
                if obj_e_type in ok_types and \
                        all(type(e) == obj_e_type for e in obj[1:]):
                    return obj_e_type
        return str

def guess_action(obj):
    return {
        bool: 'store_false' if obj else 'store_true',
    }.get(guess_type(obj), 'store')

def guess_nargs(obj):
    if guess_type(obj) == bool:
        return 0
    else:
        try:
            len(obj)
        except TypeError:
            return 1
        else:
            return '+'

class ArgFunc(object):
    @staticmethod
    def define_args(**kwargs):
        def wrapper(func):
            for (arg, attrs) in kwargs.iteritems():
                if 'default' in attrs and 'name' not in attrs:
                    attrs['name'] = '--' + arg.replace('_', '-')
                if 'dest' not in attrs and 'name' in attrs:
                    attrs['dest'] = arg
            func._argfunc_attrs = kwargs
            return func
        return wrapper

    @staticmethod
    def auto_define_args(func):
        (args, pargs, kwargs, defaults) = inspect.getargspec(func)
        if args[0] == 'self' or args[0] == 'cls':
            args = args[1:]
        defaults = defaults if defaults is not None else []
        arg_no_defaults = args[:-len(defaults)]
        arg_defaults = zip(args[-len(defaults):], defaults)
        attrs = {}
        for arg in arg_no_defaults:
            arg_attrs = {
                'metavar': arg.upper(),
            }
            attrs[arg] = arg_attrs
        for (arg, default) in arg_defaults:
            arg_attrs = {
                'name': '--' + arg.replace('_', '-'),
                'action': guess_action(default),
                'default': default,
                'dest': arg,
            }
            attrs[arg] = arg_attrs
        if pargs is not None:
            attrs[pargs] = {
                'name': pargs,
                'nargs': '*',
            }
        if kwargs is not None:
            pass
        func._argfunc_attrs = attrs
        return func


    def add_func(self, parser, func):
        if hasattr(func, '_argfunc_attrs'):
            for (arg, attrs) in func._argfunc_attrs.iteritems():
                fixed_attrs = attrs.copy()
                if 'name' in attrs:
                    command_name = fixed_attrs.pop('name')
                    fixed_attrs['dest'] = arg
                else:
                    command_name = arg
                parser.add_argument(command_name, **fixed_attrs)


    def add_obj(self, parser, obj):
        for func in (a for a in dir(obj) \
                if callable(obj, a) and hasattr(getattr(obj, a), '_argfunc_attrs')):
            self.add_func(parser, func)

class GithubActor(object):
    """
    """

    CONFIG_NS       = 'hub'
    GIT_REMOTE_NAME = 'github'

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

    def _get_padding(self, f, iterable):
        return max(len(f(i)) for i in iterable)

    @ArgFunc.define_args(
        repo_type={'choices': ('all', 'owner', 'public', 'private', 'member'), 'default': 'all'},
    )
    def repos_list(self, repo_type='all', **kwargs):
        """List your or another user's repos
        """

        repos = self._github.repos.list(
            user=kwargs.get('user', self._current_user),
            type=repo_type).all()
        padding = self._get_padding(lambda r: r.name, repos)
        for repo in repos:
            fork_icon = 'V' if repo.fork else '|'
            self._output(' {fork_icon} {name: <{padding}} -- {description}',
                fork_icon=fork_icon, padding=padding, **vars(repo))

    @ArgFunc.auto_define_args
    def repos_create(self, description='', homepage='', private=False,
            has_issues=False, has_wiki=False, has_downloads=False, in_org=None,
            **kwargs):
        """Create a new repo on GitHub
        """

        data = locals().copy()
        del data['self'], data['kwargs'], data['in_org']
        data['name'] = kwargs.get('repo', self._get_repo_name(self._current_repo))
        new_repo = self._github.repos.create(data, in_org)

    @ArgFunc.auto_define_args
    def repos_fork(self, org=None, **kwargs):
        """Fork a repo on GitHub to your account (or organization)
        """

        try:
            self._github.repos.forks.create(
                user=kwargs.get('user', self._current_user),
                repo=kwargs.get('repo', self._get_repo_name(self._current_repo)),
                org=org)
        except AssertionError:
            pass

    @ArgFunc.auto_define_args
    def repos_clone(self, **kwargs):
        repo_name = kwargs.get('repo', None)
        if repo_name is None:
            raise ValueError('Use --repo to tell me the repo name')
        try:
            github_repo = self._github.repos.get(
                user=kwargs.get('user', self._current_user),
                repo=repo_name)
        except Exception as e:
            #TODO make this not dumb
            raise e
        repo_path = os.path.join(os.getcwd(), repo_name)
        if github_repo.permissions['push']:
            git.repo.base.Repo.clone_from(github_repo.ssh_url, repo_path)
        else:
            git.repo.base.Repo.clone_from(github_repo.git_url, repo_path)
        self._output('Cloned {user}/{repo} to {path}',
            user=kwargs.get('user', self._current_user),
            repo=repo_name,
            path=repo_path)

    @ArgFunc.auto_define_args
    def repos_addremote(self, remote_name=GIT_REMOTE_NAME, **kwargs):
        """Add a remote for the corresponding repo on GitHub
        """

        actual_repo = self._current_repo
        if actual_repo is None:
            self._output('It doesn\'t look like you\'re in a git repo right now...')
        else:
            if remote_name in (rm.name for rm in actual_repo.remotes):
                self._output('Looks like the "{0}" remote already exists',
                    remote_name)
            else:
                github_repo = self._github.repos.get(
                    user=kwargs.get('user', self._current_user),
                    repo=kwargs.get('repo', self._get_repo_name(self._current_repo)))
                if github_repo.permissions['push']:
                    #read-write, use ssh url
                    actual_repo.create_remote(remote_name, github_repo.ssh_url)
                else:
                    #read only, use git url
                    actual_repo.create_remote(remote_name, github_repo.git_url)
                self._output('"{0}" remote added', remote_name)

    @ArgFunc.define_args(
        state={'choices': ('open', 'closed'), 'default': 'open'},
    )
    def pr_list(self, state='open', **kwargs):
        """List the open pull requests for a repo

        Note that the --state option is currently non-functional
        """

        pull_requests = self._github.pull_requests.list(
            user=kwargs.get('user', kwargs.get('user', self._current_user)),
            repo=kwargs.get('repo', self._get_repo_name(self._current_repo))).all()
        padding = self._get_padding(lambda pr: pr.user['login'], pull_requests)
        for pr in pull_requests:
            commit_count = len(self._github.pull_requests.list_commits(pr.number,
                user=kwargs.get('user', kwargs.get('user', self._current_user)),
                repo=kwargs.get('repo', self._get_repo_name(self._current_repo))).all())
            self._output('#{number:0>4} {commit_count:0>2}c @{user[login]: <{padding}} {title} -- <{html_url}>',
                padding=padding, commit_count=commit_count, **vars(pr))

    @ArgFunc.auto_define_args
    def pr_merge(self, pr_number, commit_message='', **kwargs):
        """Do a simple merge of a pull request (Merge Button)
        """

        self._github.pull_requests.merge(number, commit_message,
            user=kwargs.get('user', self._current_user),
            repo=kwargs.get('repo', self._get_repo_name(self._current_repo)))


def build_parser(actor):
    af = ArgFunc()
    parser = argparse.ArgumentParser(description='git-hub - Do stuff with GitHub',
        prog='git-hub')
    parser.add_argument('--verbose', help='Display more output', action='store_true')
    parser.add_argument('--user', help='Override target username', action='store', type=str)
    parser.add_argument('--repo', help='Override target repo name', action='store', type=str)
    command_parsers = parser.add_subparsers(title='GitHub commands',
        dest='command')

    #oh god wat
    command_verbs = dict((c, [v.split('_', 1)[1] for v in dir(actor) \
            if v.startswith(c+'_') and callable(getattr(actor, v))]) \
        for c in set(c.split('_')[0] for c in dir(actor) \
            if not c.startswith('_') and callable(getattr(actor, c))))

    for command in command_verbs:
        for verb in command_verbs[command]:
            cv_func = getattr(actor, command + '_' + verb)
            attrs = {}
            try:
                attrs['help'] = cv_func.__doc__.split('\n')[0].strip()
            except AttributeError:
                pass
            verb_parser = command_parsers.add_parser(command + '-' + verb, **attrs)
            af.add_func(verb_parser, cv_func)
    return parser

def main():
    actor = GithubActor()
    parser = build_parser(actor)
    result = parser.parse_args()
    command_verb = result.command + '_' + result.verb
    del result.command, result.verb
    action = getattr(actor, command_verb)
    return action(**vars(result))

if __name__ == '__main__':
    main()
