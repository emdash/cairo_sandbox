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
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk

from helpers import Point, Rect, Save, Box
import cairo
import helpers
import json
import math
import pyinotify
import threading
from queue import Queue
import sys
import time


class Logger(object):

    """Simple but featurfule logger.

    Add class-level instance for any class that needs logging
    functionality. Implements __call__ so it can be called like a
    regular method. Also works as a context manager.

    """

    enable = False

    def __init__(self, name):
        self.name = name

    def __call__(self, prefix, *args):
        """Prints a log message."""

        if self.enable:
            msg = ("%s %s " %
               (self.name, prefix) +
                " ".join((repr(arg) for arg in args)))
            print(msg, file=sys.stderr)
        else:
            return self

    def trace(self, *args):
        if self.enable:
            return self.Tracer(self, args)
        else:
            return self

    def __enter__(self, *args):
        """Dummy context manager interface when logging is disabled"""
        pass

    def __exit__(self, *args):
        """Dummy context manager interface when logging is disabled"""
        pass

    class Tracer(object):
        """Context manager logging."""
        def __init__(self, logger, args):
            self.logger = logger
            self.args = args

        def __enter__(self, *unused):
            self.logger("enter:")

        def __exit__(self, *unused):
            self.logger("exit:")


class Token(object):

    def __init__(self, source, line, index):
        self.source = source
        self.value = self.parse(source)
        self.line = line
        self.index = index
        self.transform = None

    def update_transform(self, transform):
        self.transform = transform

    def endswith(self, x):
        return self.source.endswith(x)

    def startswith(self, x):
        return self.source.startswith(x)

    def __eq__(self, other):
        return self.value == other

    def update(self, value):
        self.value = value
        self.source = str(value)

    def __hash__(self):
        return hash(self.source)

    @classmethod
    def parse(cls, token):
        try:
            return int(token)
        except:
            try:
                return float(token)
            except:
                return token


class Debuger(object):

    trace = Logger("Editor:")
    status_bar_height = 20.5
    vm_gutter_width = 125.5
    code_gutter_width = 350.5
    token_length = 55.0

    def __init__(self, reader):
        self.allowable = []
        self.transform = None
        self.reader = reader
        self.reader.start()
        self.path = sys.argv[1]
        self.prog = None
        self.load()

    def load(self):
        self.prog = compile(open(self.path, "r").read(), self.path, "exec")

    def run(self, cr, origin, scale, window_size):
        self.trace("run:")

        window = Rect.from_top_left(Point(0, 0), window_size.x, window_size.y)

        (remainder, status_bar) = window\
            .split_horizontal(window.height - self.status_bar_height)

        (content, vm_gutter) = remainder\
            .split_vertical(window.width - self.vm_gutter_width)

        with Save(cr):
            # create a new vm instance with the window as the target.
            error = None
            try:
                exec(
                    self.prog,
                    {
                        'cr': cr,
                        'cairo': cairo,
                        'window': Rect.from_top_left(Point(0, 0), content.width, content.height),
                        'scale_mm': scale,
                        'helpers': helpers
                    })
            except Exception as e:
                error = e

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

        # draw gutters around UI
        with Save(cr):
            cr.set_line_width(1.0)
            cr.move_to(*content.southwest())
            cr.rel_line_to(window.width, 0)
            cr.move_to(*vm_gutter.northwest())
            cr.line_to(*vm_gutter.southwest())
            cr.rel_line_to(0, -content.height)
            cr.stroke()

        if error is not None:
            with Box(cr, status_bar) as layout:
                cr.show_text(repr(error))


    def handle_key_event(self, event):
        self.trace("handle_key_event")

    def handle_button_press(self, event):
        pass


class ReaderThread(threading.Thread):

    env = {}
    daemon = True

    def run(self):
        while True:
            self.env = json.loads(sys.stdin.readline())


def notify_thread(debuger):

    def modified(*unused, **unused2):
        GObject.idle_add(debuger.load)

    wm = pyinotify.WatchManager()
    wm.add_watch(sys.argv[1], pyinotify.IN_MODIFY)
    notifier = pyinotify.ThreadedNotifier(wm, modified)
    notifier.daemon = True
    notifier.start()


def gui():
    def dpi(widget):
        """Return the dpi of the current monitor as a Point."""
        s = widget.get_screen()
        m = s.get_monitor_at_window(window.get_window())
        geom = s.get_monitor_geometry(m)
        mm = Point(s.get_monitor_width_mm(m),
                   s.get_monitor_height_mm(m))
        size = Point(float(geom.width), float(geom.height))
        return size / mm

    def draw(widget, cr):
        # get window / screen geometry
        alloc = widget.get_allocation()
        screen = Point(float(alloc.width), float(alloc.height))
        origin = screen * 0.5
        scale = dpi(widget)

        # excute the program
        debuger.run(cr, origin, scale, screen)

    def key_press(widget, event):
        debuger.handle_key_event(event)

    def button_press(widget, event):
        debuger.handle_button_press(event)

    def update():
        try:
            da.queue_draw()
        finally:
            return True


    GObject.timeout_add(25, update)

    debuger = Debuger(ReaderThread())
    notify_thread(debuger)

    window = Gtk.Window()
    window.set_size_request(640, 480)
    da = Gtk.DrawingArea()
    da.set_events(Gdk.EventMask.ALL_EVENTS_MASK)
    window.add(da)
    window.show_all()
    window.connect("destroy", Gtk.main_quit)
    da.connect('draw', draw)
    window.connect('key-press-event', key_press)
    window.connect('button-press-event', button_press)
    Gtk.main()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("A path to a valid python script is required.")
    else:
        import traceback
        Logger.enable = False
        gui()
