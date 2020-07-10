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
import cairo
import json
import math
import pyinotify
import threading
from queue import Queue
import re
import sys
import time


class VMError(Exception): pass
class LexError(Exception): pass


point_re = re.compile(r"^\((-?\d+(\.\d+)?),(-?\d+(\.\d+)?)\)$")


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


class Point(object):

    """Reasonably terse 2D Point class."""

    def __init__(self, x, y): self.x = float(x) ; self.y = float(y)
    def __len__(self):        return math.sqrt(self.x ** 2 + self.y ** 2)
    def __eq__(self, o):
        return isinstance(o, Point) and (self.x, self.y) == (o.x, o.y)
    def __repr__(self):       return "(%g,%g)" % (self.x, self.y)
    def __iter__(self):       yield  self.x ; yield self.y
    def __hash__(self):       return hash((self.x, self.y))
    def __bool__(self):       return False

    def binop(func):
        def impl(self, x):
            o = x if isinstance(x, Point) else Point(x, x)
            return Point(func(self.x, o.x), func(self.y, o.y))
        return impl

    __add__  = binop(lambda a, b: a + b)
    __sub__  = binop(lambda a, b: a - b)
    __mul__  = binop(lambda a, b: a * b)
    __rsub__ = binop(lambda a, b: b - a)
    __rmul__ = binop(lambda a, b: b * a)
    __truediv__  = binop(lambda a, b: a / b)
    __rtruediv__ = binop(lambda a, b: b / a)



class Rect(object):

    """Rectangle operations for layout."""

    def __init__(self, center, width, height):
        self.center = center
        self.width = width
        self.height = height

    @classmethod
    def from_top_left(self, top_left, width, height):
        return Rect(
            Point(top_left.x + width * 0.5, top_left.y + height * 0.5),
            width, height
        )

    def __repr__(self):
        return "(%s, %g, %g)" % (self.center, self.width, self.height)

    def north(self):
        return self.center + Point(0, -0.5 * self.height)

    def south(self):
        return self.center + Point(0, 0.5 * self.height)

    def east(self):
        return self.center + Point(0.5 * self.width, 0)

    def west(self):
        return self.center + Point(-0.5 * self.width, 0)

    def northwest(self):
        return self.center + Point(-0.5 * self.width, -0.5 * self.height)

    def northeast(self):
        return self.center + Point(0.5 * self.width, -0.5 * self.height)

    def southeast(self):
        return self.center + Point(0.5 * self.width, 0.5 * self.height)

    def southwest(self):
        return self.center + Point(-0.5 * self.width, 0.5 * self.height)

    def inset(self, size):
        amount = size * 2
        return Rect(self.center, self.width - amount, self.height - amount)

    def split_left(self, pos):
        return self.from_top_left(self.northwest(), pos, self.height)

    def split_right(self, pos):
        tl = self.northwest() + Point(pos, 0)
        return self.from_top_left(tl, self.width - pos, self.height)

    def split_top(self, pos):
        return self.from_top_left(self.northwest(), self.width, pos)

    def split_bottom(self, pos):
        tl = self.northwest() + Point(0, pos)
        return self.from_top_left(tl, self.width, self.height - pos)

    def split_vertical(self, pos):
        return (self.split_left(pos), self.split_right(pos))

    def split_horizontal(self, pos):
        return (self.split_top(pos), self.split_bottom(pos))

    def radius(self):
        return min(self.width, self.height) * 0.5


class VirtualPath(object):
    """Used to track the stack effects of path operations"""

    def __repr__(self):
        return "<Path>"


class VirtualContext(object):
    """Used to track the stack effects of path operations"""

    def __repr__(self):
        return "<Context>"


def frange(lower, upper, step):
    """Like xrange, but for floats."""
    accum = lower
    while accum < upper:
        yield accum
        accum += step


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


class Save(object):

    def __init__(self, cr):
        self.cr = cr

    def __enter__(self):
        self.cr.save()

    def __exit__(self, unused1, unused2, unused3):
        self.cr.restore()


class Box(object):

    def __init__(self, cr, bounds):
        self.cr = cr
        self.center = bounds.center
        self.bounds = Rect(Point(0, 0), bounds.width, bounds.height)
        (self.x, self.y) = bounds.northwest()
        self.width = bounds.width
        self.height = bounds.height

    def __enter__(self):
        self.cr.save()
        self.cr.rectangle(self.x, self.y, self.width, self.height)
        self.cr.clip()
        self.cr.translate(*self.center)
        return self.bounds

    def __exit__(self, unused1, unused2, unused3):
        self.cr.restore()


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

        # set default context state
        cr.set_source_rgb(0, 0, 0)
        cr.set_line_width(1.0)

        bounds = Rect(Point(0, 0), content.width / scale.x, content.height / scale.y)

        with Box(cr, content):
            # create a new vm instance with the window as the target.
            try:
                error = None
                exec(
                    self.prog,
                    {
                        'cr': cr,
                        'cairo': cairo,
                        'Save': Save,
                        'Box': Box,
                        'Point': Point,
                        'Rect': Rect
                    })
            except VMError as e:
                error = e

            self.transform = cr.get_matrix()
            self.inverse_transform = cr.get_matrix()
            self.inverse_transform.invert()

            # save the current point
            x, y = cr.get_current_point()

        with Save(cr):
            # stroke any residual path for feedback
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.set_operator(cairo.OPERATOR_DIFFERENCE)
            cr.set_line_width(0.1)
            cr.stroke()

        with Save(cr):
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
