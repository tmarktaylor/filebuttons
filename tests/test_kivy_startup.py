"""Test code run at kv.py import time.

This test is only valid the first time it is run in a given
Python interpreter instance.
We don't run the App.
"""

import contextlib
import sys
import unittest
from pathlib import Path
from unittest import mock


class TestCallersConfig(unittest.TestCase):

    @unittest.skipIf(sys.version_info < (3, 11), "for 3.11+")
    def test_with_callers_config(self):
        """Test user supplied config file processing."""

        # value for sys.argv when importing kv.py
        arglist = [
            "testcaseprog",
            "--",  # tell kivy following args are for the App
            "--config",
            "../config_files/aproject.ini",
        ]
        # filebuttons looks for files relative to the current working directory.
        with contextlib.chdir("docs/aproject"):
            print("\ncwd= ", Path.cwd())
            with mock.patch("sys.argv", arglist):
                import filebuttons.kv as kv

                print(f"number of columns= {kv.num_columns}")
                for c in kv.columns:
                    print(f"--- column {len(c)} items ---")
                    for d in c:
                        if d.target is None:
                            print(d.title)
                        else:
                            print(d)
                # No buttons for filename with disallowed sunbtrings.
                self.assertTrue(kv.filename_ok("abc"))
                self.assertTrue(kv.filename_ok("abc/def"))
                self.assertTrue(kv.filename_ok("abc/def.py"))
                self.assertFalse(kv.filename_ok("abc/def\n.py"))
                self.assertFalse(kv.filename_ok("\nabc/def.py"))
                self.assertFalse(kv.filename_ok("abc/def.py\n"))
                self.assertFalse(kv.filename_ok("abc||.py"))
                self.assertFalse(kv.filename_ok("abc&&.py"))
                self.assertFalse(kv.filename_ok("abc ; .py"))

                # wrapping logic at 22 characters (TEXT_WRAP_WIDTH)
                self.assertEqual(kv.wrap("a"), "a")
                # no wrap
                self.assertEqual(
                    kv.wrap("1234567890123456789012"), "1234567890123456789012"
                )
                # 1 char too long, first part is the longer part
                self.assertEqual(
                    kv.wrap("12345678901234567890123"), "123456789012\n34567890123"
                )
                # 2 char too long
                self.assertEqual(
                    kv.wrap("123456789012345678901234"), "123456789012\n345678901234"
                )


class TestDefaultConfig(unittest.TestCase):

    @unittest.skipIf(sys.version_info >= (3, 11), "for 3.9 and 3.10 only.")
    def test_default_config(self):
        """Test reading of the default config file."""
        # The default config file is here: Path().home() / ".filebuttons.ini"
        # Normally the App creates it if it does not exist.
        # However the App does not get run by these tests.
        # So we will create one here just for the test.
        # And also keep in mind we aren't changing to the aproject directory
        # so the files are chosen relative to cwd which is the root
        # of the filebuttons project.
        text = """\
[filebuttons.folders]
. = *.md
    *.txt
    *.toml
    .gitignore
src/filebuttons =
.github =
tests =

[filebuttons]
window_title = filebuttons
program = code
folder_background_color = #0c0c0cff
folder_text_color = #00a57eff
file_background_color = #595959ff
file_text_color = #38b200ff
window_height = 1000
screen_position_left = 2540
screen_position_top = 30
button_width = 160
text_wrap_width = 22
short_button_height = 18
tall_button_height = 33
spacing = 3
font_family = CourierNew
font_size = 14
"""
        configfile = Path().home() / ".filebuttons.ini"
        self.assertFalse(
            configfile.exists(),
            "Aborting test case to avoid overwriting pre-existing config file.",
        )
        configfile.write_text(text, encoding="utf-8")
        import filebuttons.kv as kv

        print(f"number of columns= {kv.num_columns}")
        for c in kv.columns:
            print(f"--- column {len(c)} items ---")
            for d in c:
                if d.target is None:
                    print(d.title)
                else:
                    print(d)
        self.assertEqual(kv.num_columns, 1)
        self.assertEqual(len(c), 12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
