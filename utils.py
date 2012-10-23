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
            print 'Cannot convert path %s: "%s"' % (
                path, ctypes.FormatError(ctypes.GetLastError()))
            return path

    def convert_to_83(path):
        return convert_path(path, ctypes.windll.kernel32.GetShortPathNameW)

    def convert_from_83(path):
        return convert_path(path,
            ctypes.windll.kernel32.GetLongPathNameW)


def prepare_path_for_env(path):
    path = os.path.expandvars(os.path.expanduser(path))

    if is_windows():
        # subprocess.Popen from Python 2.7 on Windows fails if either
        # the executable or any of the arguments contain unicode characters.
        # See http://bugs.python.org/issue1759845 for details.

        # So, if we aiming for an universal solution,
        # we need to get ANSI 8.3 version of the path and encode it for CMD.
        return convert_to_83(path).encode(locale.getpreferredencoding())

    return path


def use_forward_slashes(path):
    return path.replace('\\\\', '/').replace('\\', '/')


def universal_normalize(path):
    functions = (
        os.path.realpath,
        os.path.expanduser,
        os.path.expandvars,
        os.path.normpath,
        os.path.normcase,
        use_forward_slashes,
    )
    for func in functions:
        path = func(path)
    return path


def is_paths_equal(a, b):
    if is_windows():
        a, b = map(convert_from_83, (a, b))
    return universal_normalize(a) == universal_normalize(b)
