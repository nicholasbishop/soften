import argparse
import logging
import os
import unittest

import able
import attr
from yapf.yapflib import yapf_api

from soften import codegen, dependencies

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
    name = attr.ib()
    version = attr.ib()
    deps = attr.ib()
    repo_path = attr.ib()

    @classmethod
    def parse(cls, string, repo_path):
        parsed = able.parse(string)
        deps = dependencies.Dependencies.from_pairs(parsed['deps'])
        return cls(
            name=parsed['name'],
            version=parsed['version'],
            deps=deps,
            repo_path=repo_path)

    @classmethod
    def load(cls, path):
        repo_path = os.path.abspath(os.path.dirname(path))
        with open(path) as rfile:
            return cls.parse(rfile.read(), repo_path)


def parse_cli_args():
    parser = argparse.ArgumentParser(
        prog='soften', description='simplify python packaging')
    parser.add_argument(
        'command', nargs='?', choices=('bump', 'format', 'release', 'test'))
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


def sync(config):
    setup_py = codegen.Module(
        [
            codegen.Import('setuptools'),
            codegen.Call(
                'setuptools.setup', name=config.name, version=config.version)
        ],
        executable=True)

    path_setup_py = os.path.join(config.repo_path, 'setup.py')
    write_file(path_setup_py, str(setup_py))

    path_requirements_txt = os.path.join(config.repo_path, 'requirements.txt')
    write_file(path_requirements_txt, config.deps.format_requirements())

    ensure_package_exists(os.path.join(config.repo_path, 'tests'))


def run_tests(config):
    tests = unittest.defaultTestLoader.discover(config.repo_path)
    unittest.TextTestRunner().run(tests)


def do_release(config):
    run_tests(config)


def reformat_code(config):
    # TODO
    import glob
    for path in glob.glob(os.path.join(config.repo_path, '*/*.py')):
        yapf_api.FormatFile(path, in_place=True)


def main():
    cli_args = parse_cli_args()
    if cli_args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    config = Config.load(find_config())

    sync(config)

    if cli_args.command == 'format':
        reformat_code(config)
    elif cli_args.command == 'release':
        do_release(config)
    elif cli_args.command == 'test':
        run_tests(config)
