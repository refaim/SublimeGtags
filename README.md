# SublimeGtags
This is a plugin for the [Sublime Text 2](http://www.sublimetext.com/) text editor that support [GNU GLOBAL (gtags)](http://www.gnu.org/software/global/)

GLOBAL is a source code tagging system that works the same way across diverse environments (emacs, vi, less, bash, web browser, etc). You can locate objects in source files and move there easily. It is useful for hacking a large project containing many subdirectories, many #ifdef and many main() functions.
GLOBAL is similar to the [Ctags](http://ctags.sourceforge.net/) system (which is also supported by the ST2, see [CTags Plugin](https://github.com/SublimeText/CTags) for the details), but there are some significant differences:

    * Ctags keeps track of local variables, GLOBAL does not.
    * GLOBAL keeps track of symbol references, Ctags does not.

## Installation
Clone this repo directly into your Packages directory.

## Settings
You can point other locations for the GPATH, GRPATH etc files via the preferences.
Main Menu -> Preferences -> Package Settings -> SublimeGtags -> Settings — User

## Compatibility
SublimeGtags works on Linux, OS X and Windows.

## Support
If you find something wrong with the plugin, the documentation, or wish to request a feature, let me know on the project’s issue page.

Thanks :)

## Screenshots

### All project symbols
![](https://dl.dropbox.com/u/1696539/gtags/sublime-gtags-show-symbols.png)

### References to the specific symbol (errorMessageByCode)
![](https://dl.dropbox.com/u/1696539/gtags/sublime-gtags-find-references.png)
