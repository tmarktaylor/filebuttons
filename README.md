# filebuttons

Panel of buttons to launch files into a running IDE

[Example of the main window][screenshot]

[![license](https://img.shields.io/pypi/l/filebuttons.svg)](https://github.com/tmarktaylor/filebuttons/blob/main/LICENSE)
[![pypi](https://img.shields.io/pypi/v/filebuttons.svg)](https://pypi.python.org/pypi/filebuttons)
[![python](https://img.shields.io/pypi/pyversions/filebuttons.svg)](https://pypi.python.org/pypi/filebuttons)

[docs][readme] | [repository][src]

Employs the Kivy framework. [Kivy][kivy]

The appearance and buttons are set by the config file
in user's home folder named '.filebuttons.ini'.
A default config file is created automatically if it doesn't exist.
[Example of the Default config file][config].
Alternatively, set it with a command line option.

An instance of the target IDE should be running and the subprocess that launches the IDE
must complete right away otherwise it will block the entire filebuttons app.

By default files launch into Visual Studio Code. The application is
set by the config file.

The screen position of the main window is set by the config file so you can
have it start off on a side monitor.

Set the current working directory of the shell to the root of
the filesystem before running.

## Installation

```shell
python -m pip install filebuttons
```

## Usage

```shell
filebuttons -- -h
```

The -- unlocks the filebuttons help. Without it you get the Kivy framework help.

```text
usage: filebuttons.exe [KIVY OPTION...] [-- PROGRAM OPTIONS]:: [-h] [--title TEXT] [--config FILE]

Button panel. Each button runs a program with the file. Use to launch a file into a source code editor, IDE, or
arbitrary program.

options:
  -h, --help     show this help message and exit
  --title TEXT   Text to display in the main window title bar. Default is 'filebuttons'.
  --config FILE  Configuration file containing settings.
```

## Alternate installation

Copy [kv.py][kvfile] to a local file.

## Alternate usage

Set working directory to the root of the repository.

```shell
python <path-to-kv.py>
```

The default config file is located in the same folder as the kv.py and is
called filebuttons.ini.

## Settings

Hand edit the config file or use the main window Add Folder, Screen Coordinates,
and Settings buttons. See top of [main window][app-buttons].
The Python standard library [configparser][configparser]
describes the config file format. [Sample ini file][aproject-ini]

*Restart filebuttons to see configuration changes.*

### Folders

Files become buttons directed by the `[filebuttons.folders]` section in the config file.

- empty files are skipped
- directories starting with "__" are skipped

There is one key for each folder. The folder must be a subfolder of the
current working directory. A folder name can have `/` to indicate subdirectories.
For example `docs/fix/code =`.

The key's value is a multiline string. On each line
is a glob defined by pathlib.Path.glob [see pathlib][pathlib]. The glob selects
files from the folder to be buttons.

If the folder key has no value all files in all subdirectories get selected.
It is wise to avoid this with the root folder of a repository.

The default config file has one folder called . (dot)
which is typically the root of the repository. It is the current working directory.

Add one folder with the **Add Folder** button.

Add globs to folders by pressing Settings button and then Folders sidebar tab.
[Example][folders] Click one of the folders in the center to bring up a
multiline editing dialog. The dialog is scrolled to the bottom. Put one glob
per line.

### Program

This is the application name. The IDE.
The application name can be an absolute path or just the
name like **code** shown in the example. It should be
a name that would work when keyed in as a shell command.

[example][program]

### Appearance

[example][appearance]

### Config file

[example][configfile] Shows the location of the config file.

## Set the main window screen position

Position the main window as desired and press the Screen Coordinates
button.  [Screen Position][screen-position].

## Hints

- Both the current working directory and the config file should
  be from trusted sources.

- Files that contain either ";" or ":" will not generate buttons.

- Launch files from one repository into an IDE opened in another.

- To avoid configparser.ParsingError:, every key in `[filebuttons.folders]`
  must be followed by an `=`.

- If the recursive wildcard `**` is present in a glob, there will be
  no Folder Buttons rendered for the matching folders.

- The Folder Buttons perform no action when pressed. They act like labels.

## Issues

Exceptions are reported in Kivy's console at App close time after going to settings.

[screenshot]: https://github.com/tmarktaylor/filebuttons/blob/main/docs/screenshots/phmutest.png
[kivy]: https://kivy.org
[readme]: https://github.com/tmarktaylor/filebuttons/blob/main/README.md
[src]: https://github.com/tmarktaylor/filebuttons
[config]: https://github.com/tmarktaylor/filebuttons/blob/main/docs/config_files/default_filebuttons.ini
[kvfile]: https://github.com/tmarktaylor/filebuttons/blob/main/src/filebuttons/kv.py
[program]: https://github.com/tmarktaylor/filebuttons/blob/main/docs/screenshots/aproject-program.png
[configparser]: https://docs.python.org/3.13/library/configparser.html
[aproject-ini]: https://github.com/tmarktaylor/filebuttons/blob/main/docs/config_files/aproject.ini
[pathlib]: https://docs.python.org/3.13/library/pathlib.html
[folders]: https://github.com/tmarktaylor/filebuttons/blob/main/docs/screenshots/aproject-folders.png
[appearance]: https://github.com/tmarktaylor/filebuttons/blob/main/docs/screenshots/aproject-appearance.png
[configfile]: https://github.com/tmarktaylor/filebuttons/blob/main/docs/screenshots/aproject-config-file.png
[screen-position]: https://github.com/tmarktaylor/filebuttons/blob/main/docs/screenshots/aproject-screen-position.png
[app-buttons]: https://github.com/tmarktaylor/filebuttons/blob/main/docs/screenshots/aproject.png
