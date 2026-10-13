#!/usr/bin/python3
"""Application entry point for Pars Image Writer (GTK3 desktop launcher)."""

import os
import sys
from pathlib import Path
from typing import Optional, Sequence

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, Gtk, GLib

from MainWindow import MainWindow
from Utils import SUPPORTED_COMPRESSION_FORMATS

# All valid image extensions (case-insensitive)
SUPPORTED_EXTENSIONS = {"iso", "img", "raw", *SUPPORTED_COMPRESSION_FORMATS}


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="tr.org.pars.image-writer",
            flags=Gio.ApplicationFlags.HANDLES_OPEN | Gio.ApplicationFlags.NON_UNIQUE,
            **kwargs,
        )
        self.window: Optional[MainWindow] = None
        GLib.set_prgname("tr.org.pars.image-writer")

    def do_activate(self):
        self.window = MainWindow(self)

    def do_open(self, files: Sequence[Gio.File], filecount: int, hint: str):
        if filecount != 1:
            sys.stderr.write("Only one file can be opened at a time.\n")
            return

        target_file = files[0]
        file_path = target_file.get_path()

        if not file_path or not os.path.exists(file_path):
            sys.stderr.write(f"File does not exist: {file_path}\n")
            return

        # Case-insensitive extension extraction
        ext = Path(file_path).suffix.lstrip(".").lower()

        if ext not in SUPPORTED_EXTENSIONS:
            sys.stderr.write(
                f"Supported file extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}\n"
            )
            return

        self.window = MainWindow(self, file_path)


if __name__ == "__main__":
    app = Application()
    sys.exit(app.run(sys.argv))
