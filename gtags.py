#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import platform
import pprint
import re
import shlex
import subprocess
import unittest

PP = pprint.PrettyPrinter(indent=4)

TAGS_RE = re.compile(
    '^'
    '(?P<symbol>[^\s]+)\s+'
    '(?P<linenum>[^\s]+)\s+'
    '(?P<path>[^\s]+)\s+'
    '(?P<signature>.*)'
    '$'
)


def is_windows():
    return platform.system() == 'Windows'


def expand_path(path):
    path = os.path.expandvars(os.path.expanduser(path))
    if is_windows():
        path = path.encode('utf-8')
    return path


def find_tags_root(current, previous=None):
    current = os.path.normpath(current)
    if not os.path.isdir(current):
        return None

    parent = os.path.dirname(current)
    if parent == previous:
        return None

    if 'GTAGS' in os.listdir(current):
        return current

    return find_tags_root(parent, current)


class TagSubprocess(object):
    def __init__(self, root, extra_paths):
        environ = {
            'PATH': os.environ['PATH'],
            'GTAGSROOT': expand_path(root),
            'GTAGSLIBPATH':
                os.pathsep.join(expand_path(path) for path in extra_paths),
        }
        self.default_kwargs = { 'env': environ }
        if is_windows():
            self.default_kwargs['shell'] = True

    def create(self, command, **kwargs):
        final_kwargs = self.default_kwargs
        final_kwargs.update(kwargs)

        if isinstance(command, basestring):
            command = shlex.split(command.encode('utf-8'))

        return subprocess.Popen(command, **final_kwargs)

    def stdout(self, command, **kwargs):
        process = self.create(command, stdout=subprocess.PIPE, **kwargs)
        return process.communicate()[0]

    def call(self, command, **kwargs):
        process = self.create(command, stderr=subprocess.PIPE, **kwargs)
        retcode = process.wait()
        _, stderr = process.communicate()
        return retcode, stderr

    def status(self, command, silent=False, **kwargs):
        retcode, stderr = self.call(command, **kwargs)
        success = retcode == 0
        if not (silent or success):
            print stderr
        return success


class TagFile(object):
    def __init__(self, root, extra_paths=[]):
        self.root = root
        self.subprocess = TagSubprocess(root, extra_paths)

    def start_with(self, prefix):
        return self.subprocess.stdout('global -c %s' % prefix).splitlines()

    def _match(self, pattern, options):
        output = self.subprocess.stdout('global %s %s' % (options, pattern))
        return [match.groupdict() for match in TAGS_RE.finditer(output)]

    def match(self, pattern, reference=False):
        return self._match(pattern, '-ax' + ('r' if reference else ''))

    def rebuild(self):
        return self.subprocess.status('gtags -v', cwd=self.root)


class GTagsTest(unittest.TestCase):
    def test_start_with(self):
        f = TagFile('$HOME/repos/work/val/e4/proto1/')
        assert len(f.start_with("Exp_Set")) == 4

    def test_match(pattern):
        f = TagFile('$HOME/repos/work/val/e4/proto1/')
        matches = f.match("ExpAddData")
        assert len(matches) == 4
        assert matches[0]["path"] == "/Users/tabi/Dropbox/repos/work/val/e4/proto1/include/ExpData.h"
        assert matches[0]["linenum"] == '1463'

    def test_start_with2(self):
        f = TagFile()
        assert len(f.start_with("Exp_Set")) == 0

    def test_reference(self):
        f = TagFile('$HOME/repos/work/val/e4/proto1/')
        refs = f.match("Exp_IsSkipProgress", reference=True)
        assert len(refs) == 22
        assert refs[0]["path"] == "/Users/tabi/Dropbox/repos/work/val/e4/proto1/include/ExpPrivate.h"
        assert refs[0]["linenum"] == '1270'

    def test_extra_paths(self):
        f = TagFile("$HOME/tmp/sample", ["$HOME/repos/work/val/e4/proto1/", "~/pkg/llvm-trunk/tools/clang/"])
        matches = f.match("InitHeaderSearch")
        assert len(matches) == 1
        assert matches[0]["path"] == "/Users/tabi/pkg/llvm-trunk/tools/clang/lib/Frontend/InitHeaderSearch.cpp"
        assert matches[0]["linenum"] == '44'


if __name__ == '__main__':
    unittest.main()
