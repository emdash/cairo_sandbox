#!/usr/bin/python3
# cairo-sandbox: Interactive sandbox for cairo graphics.
#
# Copyright (C) 2020  Brandon Lewis
#
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program.  If not, see
# <https://www.gnu.org/licenses/>.


"""
Interactive sandbox for cairo vector graphics.

Prototype custom, dynamic vector graphics quickly.
"""

from __future__ import print_function

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_foreign("cairo")
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango

gi.require_version("PangoCairo", "1.0");
from gi.repository import PangoCairo

from controller import DragController
from helpers import Point, Rect, Save, Box
import params.gtk as params
from script import Script

import cairo
import helpers
import json
import math
import sys
import threading
from queue import Queue
import time
import os

try:
    from watchdog.observers import Observer
    from watchdog.events import LoggingEventHandler
    HAVE_WATCHDOG=True
except ImportError:
    print(
        "To enable auto-reload, please install `python3-watchdog`!",
        file=sys.stderr)
    HAVE_WATCHDOG=False


class ReaderThread(threading.Thread):

    env = {}
    daemon = True

    def run(self):
        while True:
            self.env = json.loads(sys.stdin.readline())


class FileWatcher(object):

    """Fire a callback when the specified file changes."""

    def __init__(self):
        self.callbacks = {}
        self.ev_handler = LoggingEventHandler()
        self.ev_handler.on_any_event = self.modified
        self.observer = Observer()

    def start(self):
        self.observer.start()

    def watchFile(self, path, callback):
        # unlike inotify, `watchdog` cannot watch a single file for
        # changes directly. instead we must watch the parent directory
        # for all events, and filter out the ones we don't care about.
        parent = os.path.split(path)[0]
        self.observer.schedule(self.ev_handler, parent, recursive=True)
        self.callbacks[path] = callback

    def modified(self, event):
        if event.event_type == "modified":
            if event.src_path in self.callbacks:
                self.callbacks[event.src_path]()


class GUI(object):

    """Gtk user interface for writing cairo_sandbox scripts."""

    if HAVE_WATCHDOG:
        fw = FileWatcher()
    reader = ReaderThread()

    def __init__(self, path):
        self.path = path
        self.param_group = None

        self.script = Script(self.path, self.reader)
        if HAVE_WATCHDOG:
            self.fw.watchFile(path, self.onFileChanged)

        self.da = Gtk.DrawingArea()
        self.da.set_events(Gdk.EventMask.ALL_EVENTS_MASK)
        self.da.connect('draw', self.draw)
        self.da.add_tick_callback(self.update)
        self.dc = DragController(self.da, self)

        self.parameters = Gtk.ScrolledWindow()
        self.parameters.connect("destroy", Gtk.main_quit)

        pane = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        pane.pack1(self.da)
        pane.pack2(self.parameters)
        pane.set_position(480)

        self.window = Gtk.Window()
        self.window.set_title("Cairo Sandbox: " + sys.argv[1])
        self.window.connect("destroy", Gtk.main_quit)
        self.window.add(pane)
        self.window.resize(1024, 768)

        self.reload()
        self.window.show_all()

    def reload(self, *unused):
        print("reloading: " + self.path)
        self.param_group = params.ParameterGroup()
        self.script.reload(self.param_group)
        self.param_group.makeWidgets(self.parameters)

    def onFileChanged(self):
        GLib.idle_add(self.reload)

    def run(self):
        if HAVE_WATCHDOG:
            self.fw.start()
        self.reader.start()
        Gtk.main()

    def update(self, widget, unused):
        try:
            widget.queue_draw()
        finally:
            return True

    def getScale(self, widget):
        """Return the dpi of the current monitor as a Point."""
        s = widget.get_screen()
        m = s.get_monitor_at_window(widget.get_window())
        geom = s.get_monitor_geometry(m)
        mm = Point(s.get_monitor_width_mm(m),
                   s.get_monitor_height_mm(m))
        size = Point(float(geom.width), float(geom.height))
        return size / mm

    def draw(self, widget, cr):
        alloc = widget.get_allocation()
        scale = self.getScale(widget)
        window = Rect.from_top_left(Point(0, 0), alloc.width, alloc.height)
        self.script.run(cr, scale, window)

    def hover(self, cursor):
        pass

    def begin(self, cursor):
        pass

    def drag(self, cursor):
        pass

    def drop(self, cursor):
        pass

    def click(self, cursor):
        cb = Gtk.Clipboard.get_default(Gdk.Display.get_default())
        cb.set_text(
            "Point(%g, %g)" % (cursor.pos.x, cursor.pos.y),
            -1
        )
        print(cursor.pos)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("A path to a valid python script is required.")
    else:
        GUI(sys.argv[1]).run()
