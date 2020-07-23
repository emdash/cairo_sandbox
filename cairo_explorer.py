#!/usr/bin/python3
# cairo-explorer: Interactive sandbox for cairo graphics.
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

from helpers import DragController, Point, Rect, Save, Box, ParameterGroup
import cairo
import helpers
import json
import math
import pyinotify
import threading
import traceback
from queue import Queue
import sys
import time


class Script(object):

    """Loads and renders a script file."""

    def __init__(self, path, reader):
        self.transform = None
        self.reader = reader
        self.load_error = None
        self.path = path
        self.prog = None
        self.param_container = None
        self.dc = None
        self.params = None

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
        self.run(cr, origin, scale, screen)

    def makeRenderWidget(self):
        da = Gtk.DrawingArea()
        da.set_events(Gdk.EventMask.ALL_EVENTS_MASK)
        da.connect('draw', self.draw)
        da.add_tick_callback(self.update)
        self.dc = DragController(da, self)
        return da

    def reload(self, container):
        path = self.path
        self.params = helpers.ParameterGroup()
        self.prog = compile(open(path, "r").read(), path, "exec")
        try:
            exec(self.prog, {
                '__name__': 'init',
                'cairo': cairo,
                'params': self.params,
                'Angle': helpers.AngleParameter,
                'Choice': helpers.ChoiceParameter,
                'Color': helpers.ColorParameter,
                'Custom': helpers.CustomParameter,
                'Font': helpers.FontParameter,
                'Image': helpers.ImageParameter,
                'Infinite': helpers.InfiniteParameter,
                'Numeric': helpers.NumericParameter,
                'Point': helpers.PointParameter,
                'Script': helpers.ScriptParameter,
                'Table': helpers.TableParameter,
                'Text': helpers.TextParameter,
                'Toggle': helpers.ToggleParameter,
            })
        except Exception as e:
            traceback.print_exc()
            self.load_error = e

        self.params.makeWidgets(container)

    def hover(self, cursor):
        pass

    def begin(self, cursor):
        pass

    def drag(self, cursor):
        pass

    def drop(self, cursor):
        pass

    def click(self, cursor):
        pass

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
                        'cursor': self.dc.cursor,
                        '__name__': 'render',
                        'params': self.params.getValues()
                    })
            except Exception as e:
                error = traceback.format_exc()

            self.transform = cr.get_matrix()
            self.inverse_transform = cr.get_matrix()
            self.inverse_transform.invert()

            # save the current point
            x, y = cr.get_current_point()

        with Save(cr):
            # stroke any residual path for feedback
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

    def key_press(self, event):
        print("key")


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
        self.wm = pyinotify.WatchManager()
        self.notifier = pyinotify.ThreadedNotifier(self.wm, self.modified)
        self.notifier.daemon = True

    def start(self):
        self.notifier.start()

    def watchFile(self, path, callback):
        self.wm.add_watch(path, pyinotify.IN_MODIFY)
        self.callbacks[path] = callback

    def modified(self, event):
        path = event.path
        self.callbacks[path]()


class GUI(object):

    """Singleton for the entire application."""

    fw = FileWatcher()
    reader = ReaderThread()

    @classmethod
    def run(self):
        self.fw.start()
        self.reader.start()
        Gtk.main()

    @classmethod
    def runScript(self, path):
        def reload():
            script.reload(parameters)
            da.set_size_request(*script.params.resolution)
            render.set_default_size(*script.params.resolution)

        script = Script(path, self.reader)
        self.fw.watchFile(path, reload)

        render = Gtk.Window()
        sw = Gtk.ScrolledWindow()
        render.set_title("Render: " + sys.path[1])
        render.add(sw)
        da = script.makeRenderWidget()
        sw.add(da)
        render.connect("destroy", Gtk.main_quit)

        parameters = Gtk.Window()
        parameters.set_title("Parameters: " + sys.argv[1])
        parameters.connect("destroy", Gtk.main_quit)

        reload()
        render.show_all()
        parameters.show_all()



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("A path to a valid python script is required.")
    else:
        GUI.runScript(sys.argv[1])
        GUI.run()
