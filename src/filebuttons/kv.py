"""Panel of buttons to launch files into a running IDE."""

import argparse
import configparser
import json
import pathlib
import shutil
import subprocess
import sys

from dataclasses import dataclass
from functools import partial
from operator import attrgetter
from pathlib import Path
from typing import Iterator, List, Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget


# This is a copy in memory only of the configuration used by App.
# This copy will not reflect changes made by the App's settings panels.
# The user needs to exit and restart the App after making changes.
# We use the config for code that runs before the App class.
# We need to make the "graphics" changes before the App class is defined.
# We never save this config file.  The App.build_config() creates the
# initial config file.
myconfig = configparser.ConfigParser()


# py src/filebuttons/kv.py -h
# Kivy Usage: kv.py [KIVY OPTION...] [-- PROGRAM OPTIONS]::
# Options placed after a '-- ' separator, will not be touched by kivy,
# and instead passed to your program.


def main_argparser() -> argparse.ArgumentParser:
    """Create argument parser."""
    program = Path(sys.argv[0]).name
    parser = argparse.ArgumentParser(
        prog=f"{program} [KIVY OPTION...] [-- PROGRAM OPTIONS]::",
        description=(
            "Button panel. Each button runs a program with the file."
            " Use to launch a file into a source code editor, IDE,"
            " or arbitrary program."
        ),
    )

    parser.add_argument(
        "--title",
        help="Text to display in the main window title bar. Default is 'filebuttons'.",
        metavar="TEXT",
        default="filebuttons",
    )

    parser.add_argument(
        "--config",
        help="Configuration file containing settings.",
        type=pathlib.Path,
        metavar="FILE",
        default=None,
    )
    return parser


parser = main_argparser()
# Kivy takes arguments before the "--" on the command line from argv.
# Kivy leaves argv[0] in place and any arguments after the "--"
# immediately follow argv[0].
# todo- the symbol args is used in a lot of places. its confusing. renames needed
args = parser.parse_args(sys.argv[1:])

if args.config:
    inifilepath = args.config
else:
    if __name__ == "__main__":
        # config file is in the same dir as this file
        appdir = Path(__file__).parent.relative_to(Path.cwd())
        inifilepath = appdir / "filebuttons.ini"
    else:
        # config file is hidden file in the users home dir
        inifilepath = Path().home() / ".filebuttons.ini"

print("reading config file", inifilepath)
myconfig.read(str(inifilepath))

if not inifilepath.exists():
    # Create a temporary config in memory with default values.
    myconfig.add_section("filebuttons.folders")
    myconfig.set("filebuttons.folders", ".", "README.md")

    myconfig.add_section("filebuttons")
    myconfig.set("filebuttons", "window_height", Config.get("graphics", "height"))
    myconfig.set("filebuttons", "screen_position_left", "100")
    myconfig.set("filebuttons", "screen_position_top", "100")

    # Values are pixels.
    myconfig.set("filebuttons", "button_width", "160")
    myconfig.set("filebuttons", "short_button_height", "18")
    myconfig.set("filebuttons", "tall_button_height", "33")
    # spacing around Buttons and Labels in the layout
    myconfig.set("filebuttons", "spacing", "3")
    myconfig.set("filebuttons", "text_wrap_width", "22")  # characters

BUTTON_WIDTH = myconfig.getint("filebuttons", "button_width")
TEXT_WRAP_WIDTH = myconfig.getint("filebuttons", "text_wrap_width")
SHORT_BUTTON = myconfig.getint("filebuttons", "short_button_height")
TALL_BUTTON = myconfig.getint("filebuttons", "tall_button_height")

SPACING = myconfig.getint("filebuttons", "spacing")


@dataclass
class Cell:
    """Label or Button text and path passed to the Button callback."""

    title: str
    target: Optional[Path] = None
    height: int = 0


def filename_ok(filename: str) -> bool:
    """Return False if filename has disallowed substrings."""
    # The intent is to prevent passing malformed filenames to a shell
    # which is possible if the ["filebuttons"]["program"] key is set to a shell
    # like (cmd on Windows or /bin/sh on Linux).
    disallow = [";", "&&", "||", "\n"]
    badfilename = any([s in filename for s in disallow])
    if badfilename:
        disallowrepr = ",".join([repr(s) for s in disallow])
        print(f"No button for {repr(filename)}. It contains some of {disallowrepr}")
        return False
    return True


def walk_one_folder(folder: Path) -> Iterator[Cell]:
    """Yield unsized Cell for non-empty/non-directory paths in folder."""
    assert folder.is_dir()
    is_visited = False
    dirs = []
    files = list(folder.iterdir())
    files.sort(key=attrgetter("name"))
    for path in files:
        if path.is_dir():
            if not path.name.startswith("__"):  # exclude __pycache__ dirs
                dirs.append(path)
        else:
            # skip empty files
            if not path.stat().st_size > 0:
                continue
            if not is_visited:
                is_visited = True
                yield Cell(title=folder.as_posix(), height=0)  # folder label
            if filename_ok(path.name):
                yield Cell(title=path.name, target=path, height=0)  # file button

    for directory in dirs:
        for unsized_cell in walk_one_folder(directory):  # recursive call
            yield unsized_cell


def emit_from_globs(start_folder: str, label: str, globs: List[str]) -> Iterator[Cell]:
    """Yield unsized Cell instance for label and for each path from globs."""
    yield Cell(title=label, target=None)  # label has no target
    paths = []
    for glob in globs:
        for path in Path(start_folder).glob(glob):
            if filename_ok(path.name):
                paths.append(path)
    unique_paths = list(set(paths))
    unique_paths.sort(key=attrgetter("name"))
    for path in unique_paths:
        yield Cell(title=path.name, target=path, height=0)


def walk_project(config: configparser.ConfigParser) -> Iterator[Cell]:
    """Yield unsized Cell instances as described by config file."""
    for key in config["filebuttons.folders"].keys():
        if not Path(key).exists():
            print(f"[filebuttons.folders] key '{key}' does not exist, skipping")
            continue
        name = "root" if key == "." else key
        if globs := config["filebuttons.folders"][key]:
            filenames = globs.splitlines()
            for unsized_cell in emit_from_globs(key, name, filenames):
                yield unsized_cell
        else:
            for unsized_cell in walk_one_folder(Path(key)):
                yield unsized_cell


def show_files(cells: Iterator[Cell]) -> None:
    """Show the cell titles, indent if the cell has a target."""
    for cell in cells:
        if cell.target is None:
            print(cell.title)  # label text
        else:
            print(" ", cell.title)  # button text


def show_heights(sized_cells: Iterator[Cell]) -> None:
    """Show wrapped label/button text and heights."""
    for cell in sized_cells:
        indent = "" if cell.target is None else "  "
        print(f"{indent}{repr(cell.title):30}  {cell.height}")


def wrap(text: str) -> str:
    """Add newline to wrap a long label/button string."""
    width = len(text)
    if width > TEXT_WRAP_WIDTH:
        index, _ = divmod(width, 2)
        # for odd width make first part the longer part
        if width % 2 == 1:
            index += 1
        text = text[:index] + "\n" + text[index:]
    return text


def compute_heights(unsized_cells: Iterator[Cell]) -> Iterator[Cell]:
    """Wrap label/button text and determine button height for each cell."""
    # Returns new Cell instances with updated title and height fields.
    for cell in unsized_cells:
        if cell.target is None:  # for button, not for label
            text = wrap(cell.title)
        else:
            text = wrap(cell.target.name)
        num_lines = text.count("\n") + 1
        if num_lines > 1:
            height = TALL_BUTTON
        else:
            height = SHORT_BUTTON
        yield Cell(text, cell.target, height)


def make_columns(
    sized_cells: Iterator[Cell], window_height: int
) -> Iterator[List[Cell]]:
    """Distribute iterable labelpaths items into columns."""
    cell_column: List[Cell] = []
    # todo- account for button spacing is [3] all faces
    minimum_height = 4 * (SHORT_BUTTON + SPACING)
    assert window_height >= minimum_height, "must be at least 4 buttons high"
    # reserve room for 4 short buttons at the top of the first column.
    column_capacity = window_height - minimum_height
    try:
        while True:
            cell = next(sized_cells)
            space_required = cell.height + SPACING
            if space_required <= column_capacity:  # room?
                cell_column.append(cell)  # yes-
                column_capacity -= space_required
            else:  # no-
                yield cell_column
                # start a new cell_column
                cell_column = []
                cell_column.append(cell)
                column_capacity = window_height - space_required
    except StopIteration:
        if cell_column:
            yield cell_column


unsized_cells = walk_project(myconfig)
sized_cells = compute_heights(unsized_cells)
window_height = myconfig.getint("filebuttons", "window_height")
columns = list(make_columns(sized_cells, window_height))
num_columns = len(columns)
layout_width = (num_columns * BUTTON_WIDTH) + SPACING


# Set kivy screen position and height of the window
print("set graphics-")
Config.set("graphics", "min_state_time", 0.0)
Config.set("graphics", "width", layout_width)
Config.set("graphics", "height", window_height)
Config.set("graphics", "position", "custom")
Config.set("graphics", "left", myconfig.getint("filebuttons", "screen_position_left"))
Config.set("graphics", "top", myconfig.getint("filebuttons", "screen_position_top"))

# Workaround to fix messed up drawing when imports are before the "graphics" changes.
from kivy.core.window import Window
from kivy.uix.settings import (
    SettingItem,
    SettingSpacer,
)
from kivy.uix.settings import SettingsWithSidebar
from kivy.uix.textinput import TextInput


def okcancel(content, validate, dismiss):
    """Add layout containing Ok and Cancel buttons/handers to content."""
    btnlayout = BoxLayout(size_hint_y=None, height="50dp", spacing="5dp")
    btn = Button(text="Ok")
    btn.bind(on_release=validate)
    btnlayout.add_widget(btn)
    btn = Button(text="Cancel")
    btn.bind(on_release=dismiss)
    btnlayout.add_widget(btn)
    content.add_widget(btnlayout)


class MyMultiLineSettingString(SettingItem):
    """Copy of SettingString with taller text input area for multiline string."""

    # Implementation of a string setting on top of a :class:`SettingItem`.
    # It is visualized with a :class:`~kivy.uix.label.Label` widget that, when
    # clicked, will open a :class:`~kivy.uix.popup.Popup` with a
    # :class:`~kivy.uix.textinput.Textinput` so the user can enter a custom
    # value.

    popup = ObjectProperty(None, allownone=True)
    """(internal) Used to store the current popup when it's shown.

    :attr:`popup` is an :class:`~kivy.properties.ObjectProperty` and defaults
    to None.
    """

    textinput = ObjectProperty(None)
    """(internal) Used to store the current textinput from the popup and
    to listen for changes.

    :attr:`textinput` is an :class:`~kivy.properties.ObjectProperty` and
    defaults to None.#00a57eff
    """

    def on_panel(self, instance, value):
        if value is None:
            return
        self.fbind("on_release", self._create_popup)

    def _dismiss(self, *args):
        if self.textinput:
            self.textinput.focus = False
        if self.popup:
            self.popup.dismiss()
        self.popup = None

    def _validate(self, instance):
        self._dismiss()
        value = self.textinput.text.strip()
        self.value = value

    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation="vertical", spacing="5dp")
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title,
            content=content,
            size_hint=(None, None),
            size=(popup_width, "250dp"),
        )
        # The textinput is taller than SettingString's.
        self.textinput = textinput = TextInput(
            text=self.value,
            font_size="24sp",
            multiline=True,
            size_hint_y=None,
            height="200sp",
            scroll_y=0,  # todo- doesn't work
        )

        textinput.bind(on_text_validate=self._validate)
        self.textinput = textinput

        # construct the content, widget are used as a spacer
        content.add_widget(Widget())
        content.add_widget(textinput)
        content.add_widget(Widget())
        content.add_widget(SettingSpacer())
        okcancel(content, self._validate, self._dismiss)
        popup.open()


class MyAddNewFolder:
    """
    Create Popup to get name of folder, add folder to the
    App's config and write the .ini file.
    """

    def __init__(self, appconfig):
        self.popup = None
        self.textinput = None
        self.appconfig = appconfig

    def _dismiss(self, *args):
        if self.popup:
            self.popup.dismiss()

    def _validate(self, instance):
        self._dismiss()
        value = self.textinput.text.strip()
        p = Path(value)
        if not p.exists():
            print(f"Not adding new folder {p} since it does not exist.")
        elif not p.is_dir():
            print(f"Not adding new folder {p} since it is not a directory.")
        elif self.appconfig.has_option("filebuttons.folders", str(p)):
            print(f"Not adding new folder {p} since it already has a setting value.")
        else:
            print(f"adding new folder '{value}' to setting [filebuttons.folders].")
            self.appconfig.set("filebuttons.folders", value, "")
            self.appconfig.write()

    def create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation="vertical", spacing="5dp")
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = Popup(
            title="Add new folder",
            content=content,
            size_hint=(None, None),
            size=(popup_width, "250dp"),
        )

        # create the textinput used to input the folder name.
        self.textinput = TextInput(
            text="", font_size="24sp", multiline=False, size_hint_y=None, height="42sp"
        )
        self.textinput.bind(on_text_validate=self._validate)

        # construct the content, widget are used as a spacer
        content.add_widget(Widget())
        content.add_widget(self.textinput)
        content.add_widget(Widget())
        content.add_widget(SettingSpacer())
        okcancel(content, self._validate, self._dismiss)
        self.popup.open()


class MyConfigureScreenPosition:
    def __init__(self, appconfig):
        self.popup = None
        self.appconfig = appconfig

    def _dismiss(self, *args):
        if self.popup:
            self.popup.dismiss()

    def popup_screen_pos(self, *args):
        """Show a popup with screen position of main window."""
        layout = BoxLayout(orientation="vertical", spacing=10)
        layout.add_widget(Label(text=f"left {Window.left}  top {Window.top}"))
        self.popup = Popup(
            title="Screen position",
            content=layout,
            size_hint=(None, None),
            size=(200, 200),
            auto_dismiss=True,
        )
        layout.add_widget(
            Button(
                text="save to settings",
                size_hint_y=0.45,
                on_release=self.save_screen_pos,
            )
        )
        layout.add_widget(
            Button(text="cancel/done", size_hint_y=0.45, on_release=self.popup.dismiss)
        )
        self.popup.open()

    def save_screen_pos(self, *args):
        self.appconfig.set("filebuttons", "screen_position_left", Window.left)
        self.appconfig.set("filebuttons", "screen_position_top", Window.top)
        self.appconfig.write()


class MyFileButton(Button):
    """Create a Button for a file described by the Path 'mytarget'."""

    def __init__(self, **kwargs):  # type: ignore
        self.mytarget = kwargs.pop("mytarget")
        super().__init__(**kwargs)
        self.bind(on_release=self.mycallback)  # note- bind is part of EventDispatcher
        self.size_hint_x = None
        self.width = BUTTON_WIDTH
        self.size_hint_y = None

    def mycallback(self, instance):
        filename = str(self.mytarget)
        print(f"file button text= {self.text}, filename={filename}")
        run_program(filename)


class MyAppButton(Button):
    """Style for App control buttons."""

    def __init__(self, **kwargs):  # type: ignore
        super().__init__(**kwargs)
        self.size_hint_max_y = SHORT_BUTTON
        self.size_hint_x = None
        self.width = BUTTON_WIDTH
        self.color = (0, 0.8, 0, 1)
        self.background_color = (0.5, 0.5, 0.5, 1)
        self.outline_color = [0.3, 0.3, 0.3, 0.3]
        self.outline_width = 1


"""Rule to display the multiline setting value on the settings panel."""
# This is from the Kivy Crash Course.
kv = """\
<ScrollableLabel>:
    text: ""
    Label:
        text: root.text
        font_size: '15sp'
        text_size: self.width, None
        size_hint_y: None
        height: self.texture_size[1]

<MyMultiLineSettingString>:
    ScrollableLabel:
        text: root.value or ''
"""


class ScrollableLabel(ScrollView):
    text = StringProperty("")


def run_program(filename) -> None:
    """Run a program with filename as the 2nd argument."""
    program = myconfig["filebuttons"]["program"]
    executable_path = shutil.which(program)
    if executable_path is None:
        print(f'Not running {program} because shutil.which("{program}") is None.')
        return
    args_list = [executable_path, filename]
    print("subprocess.run...")
    completed = subprocess.run(args_list, shell=False)
    print(f"subprocess completed returncode= {completed.returncode}")


class FilebuttonsApp(App):
    new_folder = None  # todo- should this be an object property?

    def get_application_config(self):
        """Tell the App the name of the .ini config file."""
        configfile = super(FilebuttonsApp, self).get_application_config(
            str(inifilepath)
        )
        print(f"App.get_application_config- config file is {configfile}")
        return configfile

    def build_config(self, config):
        """Override App's."""
        print("App.build_config-")

        # Save the in-memory configuration myconfig settings
        # as app configuration defalults.
        for section in myconfig.sections():
            config.setdefaults(section, dict(myconfig.items(section)))

        # Also set defaults for keys referenced after App.run().
        config.setdefaults(
            "filebuttons",
            {
                "program": "code",  # Visual Studio Code
                "folder_background_color": "#0c0c0cff",
                "folder_text_color": "#00a57fff",
                "file_background_color": "#595959ff",
                "file_text_color": "#00b200ff",
                "font_family": "CourierNew",
                "font_size": 14,
            },
        )

    @staticmethod
    def set_mainwindow_title(value, *largs):
        """Set the App's Kivy core window title bar string."""
        Window.set_title(value)

    def build(self) -> BoxLayout:
        """Override App's."""
        print("App.build-")
        self.settings_cls = SettingsWithSidebar
        self.use_kivy_settings = False

        # Set the text appearing in the titlebar of the main window.
        Clock.schedule_once(partial(self.set_mainwindow_title, args.title))

        assert self.config is not None, "Avoid pylance None nag."
        Builder.load_string(kv)
        app_layout = BoxLayout(
            orientation="horizontal", width=layout_width, padding=3, spacing=3
        )

        # App control buttons
        self.new_folder = MyAddNewFolder(self.config)
        add_folder_button = MyAppButton(
            text="Add Folder", on_release=self.new_folder.create_popup
        )

        self.screen_pos = MyConfigureScreenPosition(self.config)
        pos_button = MyAppButton(
            text="Screen Coordinates", on_release=self.screen_pos.popup_screen_pos
        )

        settings_button = MyAppButton(
            text="Settings (or press F1)", on_release=self.open_settings
        )

        quit_button = MyAppButton(text="Quit", on_release=self.stop)

        number_of_file_buttons = 0
        for column in columns:
            column_layout = GridLayout(cols=1, spacing=[SPACING])
            # Add the app control buttons to the top of first column. We reserved
            # space for them in make_columns() above.
            if column == columns[0]:
                column_layout.add_widget(add_folder_button)
                column_layout.add_widget(pos_button)
                column_layout.add_widget(settings_button)
                column_layout.add_widget(quit_button)
            for cell in column:
                if cell.target is None:
                    folder_button = Button(
                        text=cell.title,
                        size_hint_x=None,
                        width=BUTTON_WIDTH,
                        size_hint_y=None,
                        height=cell.height,
                        color=self.config["filebuttons"]["folder_text_color"],
                        background_color=self.config["filebuttons"][
                            "folder_background_color"
                        ],
                    )
                    column_layout.add_widget(folder_button)
                else:
                    number_of_file_buttons += 1
                    column_layout.add_widget(
                        MyFileButton(
                            mytarget=cell.target,
                            text=cell.title,
                            height=cell.height,
                            color=self.config["filebuttons"]["file_text_color"],
                            background_color=self.config["filebuttons"][
                                "file_background_color"
                            ],
                            font_family=self.config["filebuttons"]["font_family"],
                            font_size=self.config["filebuttons"]["font_size"],
                        )
                    )
            app_layout.add_widget(column_layout)
        print(f"{number_of_file_buttons} file buttons created.")
        return app_layout

    def build_settings(self, settings):
        """Override App's."""
        # todo- 4 key error exceptions at app exit time after closing settings.
        settings.register_type("multilinestring", MyMultiLineSettingString)
        settings.add_json_panel(
            "Folders",
            self.config,
            data=self.make_folders_json(),
        )
        settings.add_json_panel(
            "Program",
            self.config,
            data=self.make_args_json(),
        )
        settings.add_json_panel(
            "Appearance",
            self.config,
            data=self.make_appearance_json(),
        )
        settings.add_json_panel(
            "Config file",
            self.config,
            data=self.make_configfile_json(),
        )

    def make_folders_json(self):
        """Helper returns json panel data for the Folders settings."""
        setting_list = [
            {
                "type": "title",
                "title": (
                    "Empty means recurse files and folders.\n"
                    "Click to add globs.\n"
                    "Suggest add globs to top level folder"
                    " to avoid expensive recurse.\n"
                    "Restart App after changes."
                ),
            }
        ]
        assert self.config is not None, "Avoid Pylance nag."
        for k in self.config["filebuttons.folders"].keys():
            # Put in a setting for each existing key.
            if k == ".":
                setting_list.append(
                    {
                        "type": "multilinestring",
                        "title": "[b].[/b]",
                        "desc": "(top level folder)",
                        "section": "filebuttons.folders",
                        "key": ".",
                    }
                )
            else:
                setting_list.append(
                    {
                        "type": "multilinestring",
                        "title": k,
                        "desc": "",
                        "section": "filebuttons.folders",
                        "key": k,
                    }
                )
        return json.dumps(setting_list)

    def make_args_json(self):
        """Helper returns json panel data for the command line arg settings."""
        setting_list = [
            {"type": "title", "title": "Restart App after changes."},
            {
                "type": "string",
                "title": "Program name.",
                "desc": "Program to call with file.",
                "section": "filebuttons",
                "key": "program",
            },
        ]
        return json.dumps(setting_list)

    # todo- need window_height from config, currently gets from geometry?
    def make_appearance_json(self):
        """Helper returns json panel data for the appearance settings."""
        setting_list = [
            {"type": "title", "title": "Restart App after changes."},
            {
                "type": "color",
                "title": "Folder button background color",
                "desc": "",
                "section": "filebuttons",
                "key": "folder_background_color",
            },
            {
                "type": "color",
                "title": "Folder button text color",
                "desc": "",
                "section": "filebuttons",
                "key": "folder_text_color",
            },
            {
                "type": "color",
                "title": "File button background color",
                "desc": "",
                "section": "filebuttons",
                "key": "file_background_color",
            },
            {
                "type": "color",
                "title": "File button text color",
                "desc": "",
                "section": "filebuttons",
                "key": "file_text_color",
            },
            {
                "type": "numeric",
                "title": "Window height",
                "desc": "pixels",
                "section": "filebuttons",
                "key": "window_height",
            },
            {
                "type": "numeric",
                "title": "Button width",
                "desc": "pixels",
                "section": "filebuttons",
                "key": "button_width",
            },
            {
                "type": "numeric",
                "title": "Button spacing",
                "desc": "Space between buttons in pixels",
                "section": "filebuttons",
                "key": "spacing",
            },
            {
                "type": "numeric",
                "title": "Short button height",
                "desc": "Height of single line button in pixels",
                "section": "filebuttons",
                "key": "short_button_height",
            },
            {
                "type": "numeric",
                "title": "Tall button height",
                "desc": "Height of 2 line button in pixels",
                "section": "filebuttons",
                "key": "tall_button_height",
            },
            {
                "type": "numeric",
                "title": "Button text wrap width",
                "desc": "characters",
                "section": "filebuttons",
                "key": "text_wrap_width",
            },
            {
                "type": "string",
                "title": "Font",
                "desc": "File button text font family",
                "section": "filebuttons",
                "key": "font_family",
            },
            {
                "type": "numeric",
                "title": "Font Size",
                "desc": "File button text font size in pixels",
                "section": "filebuttons",
                "key": "font_size",
            },
        ]
        return json.dumps(setting_list)

    def make_configfile_json(self):
        """Helper returns json panel data showing the config file location."""
        setting_list = [
            {
                "type": "title",
                "title": "Configuation file name (read only).",
            },
            {
                "type": "title",
                "title": str(inifilepath),
            },
        ]
        return json.dumps(setting_list)


def main():
    """Entry point for the application script."""
    FilebuttonsApp().run()


if __name__ == "__main__":
    main()
