# coding=utf-8

from __future__ import print_function

import argparse
import copy
import glob
import logging
import os
import subprocess
import unittest

import able
import attr
import git
import numeric_version
from yapf.yapflib import yapf_api

from soften import codegen

LOG = logging.getLogger(__name__)


def write_file(path, content):
    with open(path, 'w') as wfile:
        wfile.write(content)
        if not content.endswith('\n'):
            wfile.write('\n')


def find_config():
    # TODO, for now just assume cwd
    return '.soften.able'


@attr.s
class Config(object):
    author = attr.ib()
    email = attr.ib()
    name = attr.ib()
    url = attr.ib()
    version = attr.ib()

    repo_path = attr.ib(default=None)
    config_path = attr.ib(default=None)
    cli_args = attr.ib(default=None)

    @classmethod
    def parse(cls, string):
        parsed = able.parse(string)
        return cls(
            author=parsed['author'],
            email=parsed['email'],
            name=parsed['name'],
            url=parsed['url'],
            version=numeric_version.NumericVersion.parse(parsed['version']))

    @classmethod
    def load(cls, path):
        with open(path) as rfile:
            config = cls.parse(rfile.read())
        config.repo_path = os.path.abspath(os.path.dirname(path))
        config.config_path = path
        return config

    def write(self):
        string = able.serialize({
            'name': self.name,
            'version': str(self.version)
        })
        # TODO(nicholasbishop): preserve comments in the file
        if not self.cli_args.dry_run:
            with open(self.config_path, 'w') as wfile:
                wfile.write(string)

    @property
    def dry_run(self):
        return self.cli_args.dry_run


def parse_cli_args():
    parser = argparse.ArgumentParser(
        prog='soften', description='simplify python packaging')
    parser.add_argument(
        'command', nargs='?', choices=('bump', 'format', 'release', 'test'))
    parser.add_argument('-d', '--dry-run', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    return parser.parse_args()


def ensure_directory_exists(path):
    if not os.path.exists(path):
        LOG.info('creating directory %s', path)
        os.makedirs(path)


def ensure_package_exists(path):
    ensure_directory_exists(path)
    path_init_py = os.path.join(path, '__init__.py')
    if not os.path.exists(path_init_py):
        LOG.info('creating empty file %s', path_init_py)
        open(path_init_py, 'w').close()


def has_main(config):
    """Return True if the package has a __main__.py."""
    path = os.path.join(config.repo_path, config.name, '__main__.py')
    return os.path.exists(path)


def git_add_files(config):
    repo = git.Repo(config.repo_path)
    repo.index.add(['.gitignore', '.soften.able', 'Pipfile', 'Pipfile.lock',
                    'setup.py', 'tests/__init__.py'])


def ensure_lines_exist(path, *lines):
    try:
        with open(path) as rfile:
            output_lines = rfile.readlines()
    except FileNotFoundError:
        output_lines = []

    for line1 in lines:
        found = False
        for line2 in output_lines:
            if line1.strip() == line2.strip():
                found = True
                break
        if not found:
            output_lines.append(line1 + '\n')

    with open(path, 'w') as wfile:
        wfile.write(''.join(output_lines))


def update_gitignore(config):
    name = '.gitignore'
    path = os.path.join(config.repo_path, name)
    ensure_lines_exist(path, '*.pyc', '__pycache__/', 'build/', 'dist/',
                       '*.egg-info/')


def get_dependencies():
    # TODO(nicholasbishop): use API if exists
    cmd = ('pipenv', 'lock', '--requirements')
    lines = subprocess.check_output(cmd).decode('utf-8').splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # TODO(nicholasbishop): keep version specifier
        parts = line.split()
        req = parts[0]
        parts = req.split('==')
        yield parts[0]


def sync(config):
    keys = {
        'name': config.name,
        'version': config.version,
        'author': config.author,
        'url': config.url,
        'author_email': config.email,
        'packages': [config.name],
        'install_requires': list(get_dependencies())
    }
    if has_main(config):
        keys['entry_points'] = {
            'console_scripts': ['soften = soften.app:main']
        }

    setup_py = codegen.Module(
        [
            codegen.Import('setuptools'),
            codegen.Call('setuptools.setup', **keys)
        ],
        executable=True)

    path_setup_py = os.path.join(config.repo_path, 'setup.py')
    write_file(path_setup_py, str(setup_py))
    os.chmod(path_setup_py, 0o777)

    ensure_package_exists(os.path.join(config.repo_path, 'tests'))
    update_gitignore(config)
    git_add_files(config)


def run_tests(config):
    tests = unittest.defaultTestLoader.discover(config.repo_path)
    unittest.TextTestRunner().run(tests)


def run_cmd(*cmd, **kwargs):
    dry_run = kwargs.get('dry_run', False)

    logging.info('%s', ' '.join(cmd))
    if not dry_run:
        subprocess.check_call(cmd)


def create_distributions(config):
    # TODO
    cmd = ['python', 'setup.py', 'build', '-v', 'sdist']
    # TODO: build has a --dry-run arg, but it makes the commend fail
    # if config.dry_run:
    #     cmd.append('--dry-run')
    run_cmd(*cmd, dry_run=config.dry_run)


def upload_distributions(config):
    # TODO
    cmd = ['twine', 'upload', '--skip-existing']
    # TODO
    cmd += list(glob.glob('dist/*'))
    run_cmd(*cmd, dry_run=config.dry_run)


def do_release(config):
    logging.debug('do_release')
    run_tests(config)
    create_distributions(config)
    upload_distributions(config)


def reformat_code(config):
    # TODO
    import glob
    for path in glob.glob(os.path.join(config.repo_path, '*/*.py')):
        yapf_api.FormatFile(path, in_place=True)


def increment_version(config):
    current = config.version
    # TODO
    major, minor, patch = list(current.parts)
    patch += 1
    new = numeric_version.NumericVersion(major, minor, patch)
    print('{} → {}'.format(current, new))
    config.version = new
    config.write()


def main():
    cli_args = parse_cli_args()
    if cli_args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    config = Config.load(find_config())
    config.cli_args = cli_args

    sync(config)

    if cli_args.command == 'bump':
        increment_version(config)
    elif cli_args.command == 'format':
        reformat_code(config)
    elif cli_args.command == 'release':
        do_release(config)
    elif cli_args.command == 'test':
        run_tests(config)
