#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools
import operator
import os
import platform
import pprint
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

PP = pprint.PrettyPrinter(indent=4)

GLOBAL_VERSION_RE = re.compile(r'^global - GNU GLOBAL (?P<version>[\d\.]+)$')

# See http://lists.gnu.org/archive/html/info-global/2010-06/msg00000.html
# for details.
GLOBAL_GSYMS_REMOVAL_VERSION = '5.9'

TAGS_RE = re.compile(
    r'^'
    r'(?P<path>(\w:)?[^:]+):'
    r'(?P<linenum>\d+):'
    r'(?P<context>.+)'
    r'$', re.MULTILINE
)


def is_windows():
    return platform.system() == 'Windows'


if is_windows():
    import ctypes
    import locale
    from ctypes.wintypes import MAX_PATH

    def convert_path(path, method):
        src = ctypes.create_unicode_buffer(path)
        dst = ctypes.create_unicode_buffer(MAX_PATH)
        if method(src, dst, ctypes.sizeof(dst)) != 0:
            return dst.value
        else:
            print 'Cannot convert path: "%s"' % (
                ctypes.FormatError(ctypes.GetLastError()))
            return None


def expand_path(path):
    path = os.path.expandvars(os.path.expanduser(path))

    if is_windows():
        # subprocess.Popen from Python 2.7 on Windows fails if either
        # the executable or any of the arguments contain unicode characters.
        # See http://bugs.python.org/issue1759845 for details.

        # So, if we aiming for an universal solution,
        # we need to get ANSI 8.3 version of the path.
        path = convert_path(path, ctypes.windll.kernel32.GetShortPathNameW)

        # And finally encode for CMD.
        path = path.encode(locale.getpreferredencoding())

    return path


class GnuGlobalVersion(object):
    def __init__(self, version_string):
        self.numbers = [int(number) for number in version_string.split('.')]

    def __cmp__(self, other):
        if isinstance(other, basestring):
            other = GnuGlobalVersion(other)

        number_pairs = itertools.izip_longest(
            self.numbers, other.numbers, fillvalue=0)
        for a, b in number_pairs:
            if a < b:
                return -1
            if a > b:
                return 1
        return 0


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
        self.default_kwargs = {'env': environ}
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
        _, stderr = process.communicate()
        return process.returncode, stderr

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
        result = []

        for match in TAGS_RE.finditer(output):
            if not is_windows():
                result.append(match.groupdict())
            else:
                data = match.groupdict()

                # Convert from CMD encoding.
                path = data['path'].decode(locale.getpreferredencoding())

                # Restore original unicode path.
                data['path'] = convert_path(path,
                    ctypes.windll.kernel32.GetLongPathNameW)

                result.append(data)

        return result

    def match(self, pattern, reference=False):
        return self._match(pattern, '--result grep -a' +
            ('r' if reference else ''))

    def rebuild(self):
        return self.subprocess.status('gtags -v', cwd=self.root)

    def version(self):
        version_string = self.subprocess.stdout('global --version').splitlines()[0]
        match = GLOBAL_VERSION_RE.match(version_string)
        if match:
            return GnuGlobalVersion(match.groupdict()['version'])
        return None


class GtagsTestCase(unittest.TestCase):
    def __init__(self, method_name):
        unittest.TestCase.__init__(self, method_name)
        self.data_folder = os.path.join(os.path.dirname(__file__), 'testdata')

    def copyData(self):
        os.mkdir(self.main_source_folder)
        os.mkdir(self.extra_source_folder)
        for root, _, files in os.walk(self.data_folder):
            for file_ in files:
                shutil.copy(os.path.join(root, file_),
                    os.path.join(self.test_folder, os.path.basename(root)))

    def setUp(self):
        self.test_folder = tempfile.mkdtemp()
        self.main_source_folder = os.path.join(self.test_folder, 'main')
        self.extra_source_folder = os.path.join(self.test_folder, 'extra')
        self.copyData()

    def tearDown(self):
        if os.path.isdir(self.test_folder):
            shutil.rmtree(self.test_folder, ignore_errors=True)

    def assertSymbol(self, symbol, signature, line, path):
        self.assertEquals(symbol['signature'].rstrip(), signature.rstrip())
        self.assertEquals(int(symbol['linenum']), line)
        self.assertEquals(os.path.realpath(symbol['path']),
            os.path.realpath(path))

    def assertVersion(self, op, v1, v2):
        self.assertTrue(op(GnuGlobalVersion(v1), GnuGlobalVersion(v2)))

    def buildGtags(self, extra_paths=[]):
        tags = TagFile(self.main_source_folder, extra_paths)
        tags.rebuild()
        return tags

    def test_version_comparison(self):
        self.assertVersion(operator.eq, '6.2.3', '6.2.3')
        self.assertVersion(operator.gt, '6.2.3', '5.2.2')
        self.assertVersion(operator.lt, '6.2.3', '6.3')

    def test_build(self):
        source_files = os.listdir(self.main_source_folder)

        tags = self.buildGtags()
        required_files = ['GPATH', 'GRTAGS', 'GSYMS', 'GTAGS']
        if tags.version() >= GLOBAL_GSYMS_REMOVAL_VERSION:
            required_files.remove('GSYMS')

        all_files = os.listdir(self.main_source_folder)
        gtags_files = set(all_files) - set(source_files)

        self.assertItemsEqual(gtags_files, required_files)
        self.assertTrue(all(
            os.path.getsize(os.path.join(self.main_source_folder, filename))
            for filename in required_files))

    def test_version(self):
        tags = self.buildGtags()
        self.assertIsInstance(tags.version(), GnuGlobalVersion)

    def test_get_by_prefix(self):
        tags = self.buildGtags()
        self.assertEquals(len(tags.start_with('')), 32)
        self.assertEquals(len(tags.start_with('LSQ')), 26)
        self.assertEquals(len(tags.start_with('foobar')), 0)

    def test_empty_match(self):
        tags = self.buildGtags()
        self.assertEquals(len(tags.match('whatever')), 0)

    def test_match(self):
        tags = self.buildGtags()
        matches = tags.match('LSQ_HandleT')
        self.assertEquals(len(matches), 1)
        handle = matches[0]
        self.assertSymbol(handle,
            signature='typedef void* LSQ_HandleT;', line=11,
            path=os.path.join(self.main_source_folder, 'linear_sequence.h'))

    def test_references(self):
        tags = self.buildGtags()
        matches = tags.match('LSQ_IteratorT', reference=True)
        self.assertEquals(len(matches), 28)
        self.assertSymbol(matches[0],
            signature='int LSQ_IsIteratorDereferencable(LSQ_IteratorT iterator) {',
            path=os.path.join(self.main_source_folder, 'doubly_linked_list.c'),
            line=56)

if __name__ == '__main__':
    tests = [
        'test_version_comparison',
        'test_build',
        'test_version',
        'test_get_by_prefix',
        'test_empty_match',
        'test_match',
        'test_references',
    ]
    suite = unittest.TestSuite(map(GtagsTestCase, tests))
    unittest.TextTestRunner(verbosity=2).run(suite)
