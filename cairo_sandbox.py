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
gi.require_foreign("cairo")
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk

from controller import DragController
from helpers import Point, Rect, Save, Box
import params.gtk as params

import cairo
import helpers
import json
import math
import sys
import threading
import traceback
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


class Script(object):

    def __init__(self, path, reader):
        self.transform = None
        self.reader = reader
        self.load_error = None
        self.path = path
        self.prog = None
        self.dc = None
        self.params = None

    def reload(self, container):
        self.params = params.ParameterGroup()
        self.prog = compile(open(self.path, "r").read(), self.path, "exec")

        try:
            exec(self.prog, {
                '__name__': 'init',
                'cairo': cairo,
                'params': self.params,
                'Angle': params.AngleParameter,
                'Choice': params.ChoiceParameter,
                'Color': params.ColorParameter,
                'Custom': params.CustomParameter,
                'Font': params.FontParameter,
                'Image': params.ImageParameter,
                'Infinite': params.InfiniteParameter,
                'Numeric': params.NumericParameter,
                'Point': params.PointParameter,
                'Script': params.ScriptParameter,
                'Table': params.TableParameter,
                'Text': params.TextParameter,
                'Toggle': params.ToggleParameter,
            })
        except BaseException as e:
            traceback.print_exc()
            self.load_error = e

        return self.params

    def run(self, cr, origin, scale, window_size):
        window = Rect.from_top_left(Point(0, 0),
                                    window_size.x, window_size.y)
        with Save(cr):
            error = None

            # Trap all errors for the script, so we can display them
            # nicely.
            try:
                exec(
                    self.prog,
                    {
                        'cr': cr,
                        'cairo': cairo,
                        'math': math,
                        'stdin': self.reader.env,
                        'window': window,
                        'scale_mm': scale,
                        'helpers': helpers.Helper(cr),
                        'Point': helpers.Point,
                        'Rect': helpers.Rect,
                        'time': time.time(),
                        '__name__': 'render',
                        'params': self.params.getValues()
                    })
            except BaseException as e:
                error = traceback.format_exc()

            self.transform = cr.get_matrix()
            self.inverse_transform = cr.get_matrix()
            self.inverse_transform.invert()

            # save the current point
            x, y = cr.get_current_point()

        with Save(cr):
            # stroke any residual path for feedback
            cr.set_operator(cairo.OPERATOR_DIFFERENCE)
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.set_line_width(0.1)
            cr.stroke()

        with Save(cr):
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.set_operator(cairo.OPERATOR_DIFFERENCE)
            # draw the current point.
            x, y = self.transform.transform_point(x, y)
            cr.translate(x, y)
            cr.move_to(-5, 0)
            cr.line_to(5, 0)
            cr.move_to(0, -5)
            cr.line_to(0, 5)
            cr.stroke()

        if error is not None:
            with Box(cr, window.inset(10), clip=False) as layout:
                cr.set_source_rgba(1.0, 0.0, 0.0, 0.5)
                cr.move_to(*layout.northwest())
                for line in error.split('\n'):
                    cr.show_text(line)
                    cr.translate(0, 10)
                    cr.move_to(*layout.northwest())


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

    """Singleton for the entire application."""

    if HAVE_WATCHDOG:
        fw = FileWatcher()
    reader = ReaderThread()
        
    def __init__(self, path):
        self.transform = None
        self.path = path
        self.param_container = None
        self.dc = None
        self.params = None

        self.script = Script(self.path, self.reader)
        if HAVE_WATCHDOG:
            self.fw.watchFile(path, on_change)

        self.render = Gtk.Window()

        # quick hack to reload file on any keypress
        self.render.connect('key-press-event', self.reload)
                
        sw = Gtk.ScrolledWindow()
        self.render.set_title("Render: " + sys.argv[1])
        self.render.add(sw)
        da = self.makeRenderWidget()
        sw.add(da)
        self.render.connect("destroy", Gtk.main_quit)

        self.parameters = Gtk.Window()
        self.parameters.set_title("Parameters: " + sys.argv[1])
        self.parameters.connect("destroy", Gtk.main_quit)

        self.reload()
        self.render.show_all()
        self.parameters.show_all()

    def reload(self, *unused):
        print("reloading: " + self.path)
        self.script.reload(self.parameters)

    def on_change(self):
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

    def dpi(self, widget):
        """Return the dpi of the current monitor as a Point."""
        s = widget.get_screen()
        m = s.get_monitor_at_window(widget.get_window())
        geom = s.get_monitor_geometry(m)
        mm = Point(s.get_monitor_width_mm(m),
                   s.get_monitor_height_mm(m))
        size = Point(float(geom.width), float(geom.height))
        return size / mm

    def draw(self, widget, cr):
        # get window / screen geometry
        alloc = widget.get_allocation()
        screen = Point(float(alloc.width), float(alloc.height))
        origin = screen * 0.5
        scale = self.dpi(widget)
        # excute the program
        self.script.run(cr, origin, scale, screen)

    def makeRenderWidget(self):
        self.da = Gtk.DrawingArea()
        self.da.set_events(Gdk.EventMask.ALL_EVENTS_MASK)
        self.da.connect('draw', self.draw)
        self.da.add_tick_callback(self.update)
        self.dc = DragController(self.da, self)
        return self.da

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
