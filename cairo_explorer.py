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

from helpers import Point, Rect, Save, Box, ParameterGroup
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


class Debuger(object):

    status_bar_height = 20.5
    vm_gutter_width = 125.5
    code_gutter_width = 350.5
    token_length = 55.0

    def __init__(self, reader, param_container):
        self.allowable = []
        self.transform = None
        self.reader = reader
        self.reader.start()
        self.path = sys.argv[1]
        self.prog = None
        self.param_container = param_container
        self.load()
        self.param_container.show_all()

    def load(self):
        self.params = helpers.ParameterGroup()
        self.prog = compile(open(self.path, "r").read(), self.path, "exec")
        try:
            exec(self.prog, {
                '__name__': 'init',
                'params': self.params,
                'Numeric': helpers.NumericParameter,
                'Text': helpers.TextParameter,
                'Color': helpers.ColorParameter,
                'Font': helpers.FontParameter,
                'Table': helpers.TableParameter,
                'Angle': helpers.AngleParameter,
                'Point': helpers.PointParameter,
                'Image': helpers.ImageParameter,
                'Script': helpers.ScriptParameter,
                'Custom': helpers.CustomParameter
            })
        except Exception as e:
            traceback.print_exc()
            self.params.logError(e)

        self.params.makeWidgets(self.param_container)

    def run(self, cr, origin, scale, window_size):
        window = Rect.from_top_left(Point(0, 0),
                                    window_size.x, window_size.y)
        with Save(cr):
            # create a new vm instance with the window as the target.
            error = None
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


    def handle_key_event(self, event):
        pass

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

    # Parameters Window
    parameters_window = Gtk.Window()
    parameters_window.set_title("Parameters: " + sys.argv[1])
    parameters_window.set_size_request(320, 480)
    parameters_window.show()

    # Debugger Window
    # XXX: use Gtk paint clock, not this ad-hoc nonsense
    GObject.timeout_add(25, update)
    debuger = Debuger(ReaderThread(), parameters_window)
    notify_thread(debuger)

    window = Gtk.Window()
    window.set_title("Preview: " + sys.argv[1])
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
        gui()
