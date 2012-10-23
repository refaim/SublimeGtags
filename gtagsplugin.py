# -*- coding: utf-8 -*-

import functools
import os
import threading

import sublime
import sublime_plugin

import gtags
from utils import *


SETTINGS_PATH = 'GTags.sublime-settings'


def load_settings():
    return sublime.load_settings(SETTINGS_PATH)


def main_thread(callback, *args, **kwargs):
    # sublime.set_timeout gets used to send things onto the main thread
    # most sublime.[something] calls need to be on the main thread
    sublime.set_timeout(functools.partial(callback, *args, **kwargs), 0)


def create_tags(root):
    return gtags.TagFile(root, load_settings().get('extra_tag_paths'))


def run_on_cwd(dir=None):
    window = sublime.active_window()

    def wrapper(func):
        view = window.active_view()

        filename = view.file_name()
        if filename is None:
            sublime.error_message('Cannot use GNU GLOBAL for non-file')
            return

        if dir is None:
            tags_root = gtags.find_tags_root(filename)
            if tags_root is None:
                sublime.error_message("GTAGS not found. build tags by 'gtags'")
                return
        else:
            tags_root = dir[0]
        func(view, create_tags(tags_root), tags_root)

    return wrapper


def selected_symbol(view):
    return view.substr(view.word(view.sel()[0]))


class ThreadProgress(object):
    def __init__(self, thread, message, success_message, error_message):
        self.thread = thread
        self.message = message
        self.success_message = success_message
        self.error_message = error_message
        self.addend = 1
        self.size = 8
        sublime.set_timeout(lambda: self.run(0), 100)

    def run(self, i):
        if not self.thread.is_alive():
            if hasattr(self.thread, 'success') and not self.thread.success:
                sublime.status_message(self.error_message)
            else:
                sublime.status_message(self.success_message)
            return

        before = i % self.size
        after = (self.size - 1) - before
        sublime.status_message('%s [%s=%s]' % \
            (self.message, ' ' * before, ' ' * after))
        if not before:
            self.addend = 1
        elif not after:
            self.addend = -1
        i += self.addend
        sublime.set_timeout(lambda: self.run(i), 100)


class GtagsDispatcher(object):
    instance = None

    def __init__(self):
        self.cache = {}
        self.jumps = {}

    def jump_history(self, root):
        root = universal_normalize(root)
        if root not in self.jumps:
            self.jumps[root] = JumpHistory()
        return self.jumps[root]

    def store_in_cache(self, root, symbols):
        self.cache[universal_normalize(root)] = symbols

    def load_from_cache(self, root):
        return self.cache.get(universal_normalize(root), None)

    def clear_cache_entry(self, root):
        self.store_in_cache(root, None)


def dispatcher():
    if GtagsDispatcher.instance is None:
        GtagsDispatcher.instance = GtagsDispatcher()
    return GtagsDispatcher.instance


class JumpHistory(object):
    instance = None

    def __init__(self):
        self._storage = []

    def append(self, view):
        filename = view.file_name()
        row, col = view.rowcol(view.sel()[0].begin())
        encoded = '%s:%d:%d' % (filename, row + 1, col + 1)
        if self._storage and self._storage[-1] == encoded:
            return
        self._storage.append(encoded)

    def jump_back(self):
        if self.empty():
            sublime.status_message('Jump history is empty')
        else:
            filename = self._storage.pop()
            sublime.active_window().open_file(filename, sublime.ENCODED_POSITION)

    def jump_forward(self):
        sublime.status_message('Not implemented')

    def empty(self):
        return len(self._storage) == 0


class GtagsJumpBack(sublime_plugin.WindowCommand):
    def run(self):
        file_name = sublime.active_window().active_view().file_name()
        if file_name:
            tags_root = gtags.find_tags_root(file_name)
            if tags_root is not None:
                dispatcher().jump_history(tags_root).jump_back()


def gtags_jump_keyword(view, keywords, root, showpanel=False):
    def jump(keyword):
        dispatcher().jump_history(root).append(view)
        position = '%s:%d:0' % (
            os.path.normpath(keyword['path']), int(keyword['linenum']))
        view.window().open_file(position, sublime.ENCODED_POSITION)

    def on_select(index):
        if index != -1:
            jump(keywords[index])

    if showpanel or len(keywords) > 1:
        if load_settings().get('show_relative_paths'):
            convert_path = lambda path: os.path.relpath(path, root)
        else:
            convert_path = os.path.normpath
        data = [
            [kw['context'].strip(),
             '%s:%d' % (convert_path(kw['path']), int(kw['linenum']))]
             for kw in keywords
        ]
        view.window().show_quick_panel(data, on_select)
    else:
        jump(keywords[0])


class ShowSymbolsThread(threading.Thread):
    def __init__(self, view, tags, root, is_caching_allowed):
        threading.Thread.__init__(self)
        self.view = view
        self.tags = tags
        self.root = root
        self.is_caching_allowed = is_caching_allowed

    def run(self):
        symbols = None
        if self.is_caching_allowed:
            symbols = dispatcher().load_from_cache(self.root)
        if symbols is None:
            symbols = self.tags.by_prefix('')
        if self.is_caching_allowed:
            dispatcher().store_in_cache(self.root, symbols)
        self.success = len(symbols) > 0
        if not self.success:
            return

        def on_select(index):
            if index != -1:
                definitions = self.tags.match(symbols[index])
                gtags_jump_keyword(self.view, definitions, self.root)

        sublime.set_timeout(
            lambda: self.view.window().show_quick_panel(symbols, on_select), 0)


class GtagsShowSymbols(sublime_plugin.TextCommand):
    def run(self, edit):
        @run_on_cwd()
        def and_then(view, tags, root):
            thread = ShowSymbolsThread(view, tags, root,
                load_settings().get('cache_search_results'))
            thread.start()
            ThreadProgress(thread,
                'Getting symbols on %s' % root,
                'Symbols have successfully obtained',
                'No symbols found')


class GtagsSearchCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        @run_on_cwd()
        def and_then(view, tags, root):
            symbol = selected_symbol(view)
            matches = self.match(tags, symbol)
            if matches:
                gtags_jump_keyword(view, matches, root,
                    showpanel=load_settings().get('show_panel_for_single_match'))
            else:
                sublime.status_message(self.not_found() % symbol)


class GtagsNavigateToDefinition(GtagsSearchCommand):
    def match(self, tags, symbol):
        return tags.match(symbol)

    def not_found(self):
        return 'The symbol "%s" was not found'


class GtagsFindReferences(GtagsSearchCommand):
    def match(self, tags, symbol):
        return tags.match(symbol, reference=True)

    def not_found(self):
        return 'References to "%s" were not found'


class TagsRebuildThread(threading.Thread):
    def __init__(self, tags):
        threading.Thread.__init__(self)
        self.tags = tags

    def run(self):
        self.success = self.tags.rebuild()


class GtagsRebuildTags(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        # Set root folder if used from sidebar context menu.
        root = kwargs.get('dirs')

        @run_on_cwd(dir=root)
        def and_then(view, tags, root):
            thread = TagsRebuildThread(tags)
            thread.start()
            ThreadProgress(thread,
                'Rebuilding tags on %s' % root,
                'Tags rebuilt successfully on %s' % root,
                'Error while tags rebuilding, see console for details')


class AutoUpdateThread(threading.Thread):
    def __init__(self, tags, file_name):
        threading.Thread.__init__(self)
        self.tags = tags
        self.file_name = file_name

    def run(self):
        self.success = self.tags.update_file(self.file_name)

        def clear_cache(tags_root):
            dispatcher().clear_cache_entry(tags_root)

        main_thread(clear_cache, self.tags.root)


class GtagsAutoUpdate(sublime_plugin.EventListener):
    def on_post_save(self, view):
        if not load_settings().get('update_on_save'):
            return
        file_name = view.file_name()
        tags_root = gtags.find_tags_root(file_name)
        if tags_root is not None:
            tags = create_tags(tags_root)
            if not tags.is_single_update_supported():
                print ('Incremental single file update is not supported' + ' ' +
                       'until GNU GLOBAL v%s. You have GNU GLOBAL v%s.') % (
                    gtags.GLOBAL_SINGLE_UPDATE_ARRIVAL_VERSION,
                    tags.version())
                return
            thread = AutoUpdateThread(tags, file_name)
            thread.start()
            ThreadProgress(thread,
                'Updating tags for %s' % file_name,
                'Tags updated successfully for %s' % file_name,
                'Error while tags updating, see console for details')
