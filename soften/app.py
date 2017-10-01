import argparse
import os

import able
import attr

from soften import codegen, dependencies


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
        return cls(name=parsed['name'],
                   version=parsed['version'],
                   deps=deps,
                   repo_path=repo_path)

    @classmethod
    def load(cls, path):
        with open(path) as rfile:
            return cls.parse(rfile.read(), os.path.dirname(path))


def parse_cli_args():
    parser = argparse.ArgumentParser(prog='soften', description='simplify python packaging')
    parser.add_argument('command', nargs='?', choices=('bump', 'release'))
    return parser.parse_args()


def sync(config):
    setup_py = codegen.Module([
        codegen.Import('setuptools'),
        codegen.Call('setuptools.setup',
                     name=config.name,
                     version=config.version)],
                              executable=True)

    path_setup_py = os.path.join(config.repo_path, 'setup.py')
    write_file(path_setup_py, str(setup_py))

    path_requirements_txt = os.path.join(config.repo_path, 'requirements.txt')
    write_file(path_requirements_txt, config.deps.format_requirements())


def main():
    cli_args = parse_cli_args()

    config = Config.load(find_config())

    sync(config)
