# -*- coding: utf-8 -*-

import os
import platform


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

    def convert_to_83(path):
        path = convert_path(path, ctypes.windll.kernel32.GetShortPathNameW)
        # And finally encode for CMD.
        return path.encode(locale.getpreferredencoding())

    def convert_from_83(path):
        # Convert from CMD encoding.
        path = path.decode(locale.getpreferredencoding())
        # Restore original unicode path.
        return convert_path(path,
            ctypes.windll.kernel32.GetLongPathNameW)


def use_forward_slashes(path):
    return path.replace('\\\\', '/').replace('\\', '/')


def expand_path(path):
    path = os.path.expandvars(os.path.expanduser(path))

    if is_windows():
        # subprocess.Popen from Python 2.7 on Windows fails if either
        # the executable or any of the arguments contain unicode characters.
        # See http://bugs.python.org/issue1759845 for details.

        # So, if we aiming for an universal solution,
        # we need to get ANSI 8.3 version of the path and encode it for CMD.
        path = convert_to_83(path)

    return path


def is_paths_equal(a, b):
    op = os.path
    normalize = lambda path: op.normcase(op.normpath(op.realpath(path)))
    if is_windows():
        a, b = map(convert_from_83, (a, b))
    return normalize(a) == normalize(b)
