# -*- coding: utf-8 -*-

import itertools
import locale
import os
import re
import shlex
import subprocess

from utils import *

GLOBAL_VERSION_RE = re.compile(r'^global - GNU GLOBAL (?P<version>[\d\.]+)$')

# See http://lists.gnu.org/archive/html/info-global/2009-10/msg00000.html
# for details
GLOBAL_SINGLE_UPDATE_ARRIVAL_VERSION = '5.7.6'

# See http://lists.gnu.org/archive/html/info-global/2010-03/msg00001.html
# for details
GLOBAL_NEW_PARSER_ARRIVAL_VERSION = '5.8.2'

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


class GlobalVersion(object):
    def __init__(self, version_string):
        self.numbers = [int(number) for number in version_string.split('.')]
        self.string = version_string

    def __cmp__(self, other):
        if isinstance(other, basestring):
            other = GlobalVersion(other)

        number_pairs = itertools.izip_longest(
            self.numbers, other.numbers, fillvalue=0)
        for a, b in number_pairs:
            if a < b:
                return -1
            if a > b:
                return 1
        return 0

    def __str__(self):
        return self.string


def find_tags_root(current, previous=None):
    current = os.path.normpath(current)
    if not os.path.isdir(current):
        return find_tags_root(os.path.dirname(current))

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
            'GTAGSROOT': prepare_path_for_env(root),
            'GTAGSLIBPATH': os.pathsep.join(
                prepare_path_for_env(path) for path in extra_paths),
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

    def version(self):
        version_string = self.subprocess.stdout('global --version').splitlines()[0]
        match = GLOBAL_VERSION_RE.match(version_string)
        if match:
            return GlobalVersion(match.groupdict()['version'])
        return None

    def by_prefix(self, prefix):
        return self.subprocess.stdout('global -c %s' % prefix).splitlines()

    def _match(self, pattern, options):
        output = self.subprocess.stdout('global %s %s' % (options, pattern))
        result = []

        for match in TAGS_RE.finditer(output):
            data = match.groupdict()
            if is_windows():
                # Convert from CMD encoding.
                path = data['path'].decode(locale.getpreferredencoding())
                # Restore original unicode path.
                data['path'] = convert_from_83(path)
            result.append(data)

        return result

    def match(self, pattern, reference=False):
        return self._match(pattern, '--result grep -a' +
            ('r' if reference else ''))

    def rebuild(self):
        return self.subprocess.status('gtags -v', cwd=self.root)

    def is_single_update_supported(self):
        return self.version() >= GLOBAL_SINGLE_UPDATE_ARRIVAL_VERSION

    def update_file(self, path):
        if not self.is_single_update_supported():
            return False
        if is_windows():
            path = use_forward_slashes(path)
        return self.subprocess.status('gtags --single-update %s' % path,
            cwd=self.root)
