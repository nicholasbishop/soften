# pylint: disable=missing-docstring

import unittest

from pyfakefs import fake_filesystem_unittest

from soften import app


def make_config():
    return app.Config(author='Mock Author',
                      email='author@mock.com',
                      name='mypkg',
                      url='mypkg.mock.com',
                      version='1.2.3')


class TestSoften(unittest.TestCase):
    """Uncategorized tests."""

    def test_has_main(self):
        config = make_config()
        config.repo_path = '/myRepo'
        with fake_filesystem_unittest.Patcher() as patcher:
            self.assertFalse(app.has_main(config))
            patcher.fs.CreateFile('/myRepo/mypkg/__main__.py')
            self.assertTrue(app.has_main(config))
