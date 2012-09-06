#!/usr/bin/env python

""" Git plugin for GitHub integration
"""

import argparse
import os
try:
    import ConfigParser
except ImportError: #renamed in py3k
    import configparser as ConfigParser

import git
import pygithub3

def create_parser():
    parser = argparse.ArgumentParser(description='git-hub - Do stuff with GitHub',
        prog='git-hub')
    parser.add_argument('namespace')
    parser.add_argument('verb')
    parser.add_argument('options', nargs='*')
    return parser

def init_github(repo):
    if repo is None:
        if os.path.exists(os.path.expanduser('~/.gitconfig')):
            cfg = git.config.GitConfigParser(os.path.expanduser('~/.gitconfig'))
        else:
            raise ValueError('Can\'t find a config file for github login info')
    else:
        cfg = repo.config_reader()
    gh_username = cfg.get_value('hub', 'username')
    gh_password = cfg.get_value('hub', 'password')
    repo_name = os.path.basename(repo.working_tree_dir) \
        if repo is not None else None
    gh = pygithub3.Github(login=gh_username, user=gh_username,
        password=gh_password, repo=repo_name)
    return gh

def init_repo():
    try:
        repo = git.Repo(os.getcwd())
    except git.exc.InvalidGitRepositoryError as err:
        repo = None
    return repo

def handle_parsed(parser_result, gh, repo):
    if parser_result.namespace == 'repos':
        if parser_result.verb == 'create':
            repo = gh.repos.create(data=dict(
                name=parser_result.options[0],
                description=' '.join(parser_result.options[1:])))
            print repo, vars(repo)

def main():
    repo = init_repo()
    gh = init_github(repo)
    parser = create_parser()
    handle_parsed(parser.parse_args(), gh, repo)

if __name__ == '__main__':
    main()
