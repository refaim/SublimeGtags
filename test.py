#!/usr/bin/env python
# -*- coding: utf-8 -*-

import marshal
import operator
import os
import shutil
import tempfile
import unittest

import gtags
from utils import *


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
        self.assertEquals(symbol['context'].rstrip(), signature.rstrip())
        self.assertEquals(int(symbol['linenum']), line)
        self.assertTrue(is_paths_equal(symbol['path'], path))

    def assertVersion(self, op, v1, v2):
        self.assertTrue(op(gtags.GlobalVersion(v1), gtags.GlobalVersion(v2)))

    def buildGtags(self, extra_paths=[]):
        tags = gtags.TagFile(self.main_source_folder, extra_paths)
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
        if tags.version() >= gtags.GLOBAL_GSYMS_REMOVAL_VERSION:
            required_files.remove('GSYMS')

        all_files = os.listdir(self.main_source_folder)
        gtags_files = set(all_files) - set(source_files)

        self.assertEqual(sorted(gtags_files), sorted(required_files))
        self.assertTrue(all(
            os.path.getsize(os.path.join(self.main_source_folder, filename))
            for filename in required_files))

    def test_version(self):
        tags = self.buildGtags()
        self.assertTrue(isinstance(tags.version(), gtags.GlobalVersion))

    def test_get_by_prefix(self):
        tags = self.buildGtags()
        self.assertEquals(len(tags.by_prefix('')), 32)
        self.assertEquals(len(tags.by_prefix('LSQ')), 26)
        self.assertEquals(len(tags.by_prefix('foobar')), 0)

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
        if tags.version() >= gtags.GLOBAL_NEW_PARSER_ARRIVAL_VERSION:
            refcount = 28
            line = 56
            signature = 'int LSQ_IsIteratorDereferencable(LSQ_IteratorT iterator) {'
        else:
            refcount = 6
            line = 75
            signature = 'LSQ_IteratorT LSQ_GetElementByIndex(LSQ_HandleT handle, LSQ_IntegerIndexT index) {'
        self.assertEquals(len(matches), refcount)
        self.assertSymbol(matches[0],
            signature=signature,
            path=os.path.join(self.main_source_folder, 'doubly_linked_list.c'),
            line=line)

    def test_single_update(self):
        tags = self.buildGtags()
        symbol_name = 'LSQ_IteratorT'
        old_matches = tags.match(symbol_name, reference=True)
        file_name = os.path.join(old_matches[0]['path'])
        open(file_name, 'a').write(symbol_name)
        tags.update_file(file_name)
        new_matches = tags.match(symbol_name, reference=True)
        serialize = lambda matches: set(marshal.dumps(match) for match in matches)
        difference = serialize(new_matches) - serialize(old_matches)
        self.assertEquals(len(difference), 1)
        self.assertTrue(list(difference)[0] not in old_matches)

if __name__ == '__main__':
    tests = [
        'test_version_comparison',
        'test_build',
        'test_version',
        'test_get_by_prefix',
        'test_empty_match',
        'test_match',
        'test_references',
        'test_single_update'
    ]
    suite = unittest.TestSuite(map(GtagsTestCase, tests))
    unittest.TextTestRunner(verbosity=2).run(suite)
