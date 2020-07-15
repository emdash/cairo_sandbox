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

from collections import OrderedDict
import cairo
import math


import gi
gi.require_version("Gtk", "3.0")
gi.require_foreign("cairo")
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk


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


class Save(object):

    """A context manager which Keeps calls to save() and restore() balanced."""

    def __init__(self, cr):
        self.cr = cr

    def __enter__(self):
        self.cr.save()

    def __exit__(self, unused1, unused2, unused3):
        self.cr.restore()


class Box(object):

    """A context manager which centers within the given rectangle.

    Implicitly calls save() / and restore. If clip is True, also clips
    to the rectangle.
    """

    def __init__(self, cr, bounds, clip=True):
        self.cr = cr
        self.center = bounds.center
        self.bounds = Rect(Point(0, 0), bounds.width, bounds.height)
        (self.x, self.y) = bounds.northwest()
        self.width = bounds.width
        self.height = bounds.height
        self.clip = clip

    def __enter__(self):
        self.cr.save()
        self.cr.rectangle(self.x, self.y, self.width, self.height)
        if self.clip:
            self.cr.clip()
        self.cr.translate(*self.center)
        return self.bounds

    def __exit__(self, unused1, unused2, unused3):
        self.cr.restore()


class Parameter(object):

    """A uniform interface for creating named parameters"""

    def require(self, value, allowed_types):
        given = type(value)
        if given not in allowed_types:
            raise TypeError("Expected one of %s, got %r." % (
                ", ".join(repr(t) for t in allowed_types),
                given
            ))

    def makeWidget(self):
        raise NotImplementedError()

    def getValue(self):
        raise NotImplementedError()


class NumericParameter(Parameter):

    def __init__(self, lower=0, upper=1, step=1/128, default=0.5):
        allowed = {int, float, complex, type(None)}
        self.require(lower, allowed)
        self.require(upper, allowed)
        self.require(default, allowed)
        self.lower = lower
        self.upper = upper
        self.step = step
        self.default = default

    def makeWidget(self):
        self.adjustment = Gtk.Adjustment(
            self.default,
            self.lower,
            self.upper,
            self.step)
        if self.lower is not None and self.upper is not None:
            self.widget = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, self.adjustment)
            self.widget.set_draw_value(True)
        else:
            self.widget = Gtk.SpinButton.new(self.adjustment, self.step / 4, 3)

        self.widget.show()
        return self.widget

    def getValue(self):
        return self.adjustment.get_value()


# TBD: images, gradients, stipples, etc.
class ColorParameter(Parameter):

    def __init__(self, r=0, g=0, b=0, a=1.0):
        self.default = (r, g, b, a)
        self.require(r, {int, float})
        self.require(g, {int, float})
        self.require(b, {int, float})
        self.require(a, {int, float})

    def makeWidget(self):
        self.widget = Gtk.ColorButton.new_with_rgba(Gdk.RGBA(*self.default))
        return self.widget

    def getValue(self):
        gdk_color = self.widget.get_color()
        r, g, b = gdk_color.to_floats()
        return cairo.SolidPattern(r, g, b, self.widget.get_alpha())


class TextParameter(Parameter):

    def __init__(self, default=None):
        self.require(default, {str, None})
        self.value = default
        self.widget = None

    def makeWidget(self):
        self.widget = Gtk.TextView()
        if self.value is not None:
            self.widget.get_buffer().set_text(self.value)
        self.widget.show()
        self.widget.set_editable(True)
        return self.widget

    def getValue(self):
        buf = self.widget.get_buffer()
        return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)


class TableParameter(Parameter):

    def __init__(self, row_type, default=None):
        self.require(row_type, {list, tuple})
        for item in row_type:
            self.require(item, {str, int, float, long, Point, Color})
        self.row_type = row_type
        self.value = default


class PointParam(Parameter):

    def __init__(self, default=None):
        self.require(default, {Point, None})
        self.value = default


class AngleParameter(Parameter):

    """Special-case of NumericParameter with wrapping range between 0 - 2pi.
    """

    def __init__(self, default=None):
        self.require(default, {float, None})
        self.value = default


class ParameterGroup(object):

    def __init__(self):
        self.params = OrderedDict()
        self.error = None

    def define(self, name, param):
        if name in self.params:
            raise ValueError("Parameter %s already defined" % name)
        self.params[name] = param

    def makeWidgets(self, container):
        for name, param in self.params.items():
            print(name, param)
            box = Gtk.Box(Gtk.Orientation.HORIZONTAL, spacing=6)
            box.pack_start(Gtk.Label(name), False, False, 12)
            box.pack_end(param.makeWidget(), True, True, 12)
            row = Gtk.ListBoxRow()
            row.add(box)
            container.add(row)

    def getValues(self):
        return {name: param.getValue()
                for name, param in self.params.items()}

    def logError(self, error):
        self.error = error
