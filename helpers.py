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


class Helper(object):

    """Provide useful methods not available in the standard cairo API."""

    def __init__(self, cr):
        self.cr = cr

    def circle(self, center, radius):
        self.cr.arc(center.x, center.y, radius, 0, 2 * math.pi)

    def center_rect(self, center, w, h):
        self.cr.rectangle(center.x - 0.5 * w, center.y - 0.5 * h, w, h)

    def center_round_rect(self, center, w, h):
        raise NotImplementedError()

    def rect(self, rect):
        self.center_rect(rect.center, rect.width, rect.height)

    def round_rect(self, rect):
        self.round_rect(rect.center, rect.width, rect.height)

    def move_to(self, point):
        self.cr.move_to(*point)

    def line_to(self, point):
        self.cr.line_to(*point)

    def curve_to(self, a, b, c):
        self.cr.curve_to(a.x, a.y, b.x, b.y, c.x, c.y)

    def polygon(self, *points, close=True):
        self.move_to(points[0])
        for point in points:
            self.line_to(point)
        if close:
            self.cr.close()

    def curve(self, close=False, *points):
        raise NotImplementedError()

    def save(self):
        return Save(self.cr)

    def box(self, rect, clip=True):
        return Box(self.cr, rect, clip)


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

    """A uniform interface for creating live-adjustable parameters."""

    def require(self, value, allowed_types):
        """Raise an error if `value` is not one of `allowed_types`.

        `allowed_types` may be a tuple or a single type.
        """

        if not isinstance(value, allowed_types):
            raise TypeError("Expected one of %s, got %r." % (
                ", ".join(repr(t) for t in allowed_types),
                given
            ))


    def makeWidget(self):
        """Return a Gtk.Widget for this parameter type.

        This should be overridden in subtypes to return something
        appropriate for the quantity represented by the parameter.

        In addition, subtypes should cache whatever data needed to
        retrive the current parameter value from the widget.
        """
        return Gtk.Label("Not Implemented")

    def getValue(self):
        """Return the current value for this parameter.

        This should be overridden in supbtypes to return the current
        widget value.
        """
        return self.default


class AngleParameter(Parameter):

    """A numeric value clamped between 0 and 2 * math.pi."""

    def __init__(self, default=None):
        self.require(default, (float, None))
        self.default = default


class ChoiceParameter(Parameter):

    """A parameter representing a choice of alternatives.
    """

    def __init__(self, alternatives, default):
        # XXX: should be any seq
        self.require(alternatives, (tuple, list, map))
        self.alternatives = alternatives


# TBD: images, gradients, stipples, etc.
class ColorParameter(Parameter):

    """An RGBA Color value."""

    def __init__(self, r=0, g=0, b=0, a=1.0):
        self.default = (r, g, b, a)
        self.require(r, (int, float))
        self.require(g, (int, float))
        self.require(b, (int, float))
        self.require(a, (int, float))

    def makeWidget(self):
        self.widget = Gtk.ColorButton.new_with_rgba(Gdk.RGBA(*self.default))
        return self.widget

    def getValue(self):
        gdk_color = self.widget.get_color()
        r, g, b = gdk_color.to_floats()
        return cairo.SolidPattern(r, g, b, self.widget.get_alpha())


class CustomParameter(Parameter):

    """A parameter that YOU have implemented."""

    def __init__(self, path):
        self.require(path, str)
        self.path = str

class FontParameter(Parameter):

    """An easy way to chose a specific font."""

    def __init__(self, default=None):
        self.require(default, (str, None))
        self.default = default
        self.widget = None


class ImageParameter(Parameter):

    """A convenient way to load an image from disk.

    If loading succeeds, the will be converted to a cairo.ImagePattern.
    """

    def __init__(self, alternatives, default):
        # XXX: should be any seq
        self.require(alternatives, (tuple, list, map))
        self.alternatives = alternatives


class InfiniteParameter(Parameter):

    """A scalar value that is not constrained to a finite interval."""

    def __init__(self, default):
        self.require(default, (float, int, None))
        self.default = default


class NumericParameter(Parameter):

    """A scalar numeric value, with a finite range."""

    def __init__(self, lower=0, upper=1, step=1/128, default=0.5):
        allowed = (int, float, complex, None)
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
            self.widget = Gtk.Scale.new(
                Gtk.Orientation.HORIZONTAL,
                self.adjustment)
            self.widget.set_draw_value(True)
        else:
            self.widget = Gtk.SpinButton.new(self.adjustment, self.step / 4, 3)

        self.widget.show()
        return self.widget

    def getValue(self):
        return self.adjustment.get_value()


class PointParameter(Parameter):

    """An (x,y) pair, returned as a helpers.Point instance."""

    def __init__(self, default=None):
        self.require(default, (Point, None))
        self.default = default


class ScriptParameter(Parameter):

    """A convenient way to select a child script from disk.

    This allows delegating a portion of the image to another script.

    If the file exists, it will be loaded and compiled to a
    `helpers.ChildScript` object. Any parameters required by the
    script will be visible in a separate parameter window.

    You can render the script into the current context by calling
    `render()` on the parameter object.

    If `stdin` is None, then stdin will be will be automatically
    available in the child script as well, otherwise stdin must be a
    `dict` containing any values the child script requires.
    """

    def __init__(self, default=None, stdin=None):
        # XXX: should be any seq
        self.require(default, str)
        self.require(stdin, dict)


class TableParameter(Parameter):

    """An arbitrary of values, which may themelves be tuples."""

    def __init__(self, row_type, default=None):
        self.require(row_type, (list, tuple))
        for item in row_type:
            self.require(item, (str, int, float, long, Point, Color))
        self.row_type = row_type
        self.default = default


class TextParameter(Parameter):

    """An arbitrary text string."""

    def __init__(self, default=None, multiline=False):
        self.require(default, (str, None))
        self.require(multiline, bool)
        self.default = default
        self.multiline = multiline
        self.widget = None

    def makeWidget(self):
        if self.multiline:
            self.widget = Gtk.TextView()

            if self.default is not None:
                self.widget.get_buffer().set_text(self.default)
                self.widget.show()
                self.widget.set_editable(True)
        else:
            self.widget = Gtk.Entry.new()
            if self.default is not None:
                self.widget.set_text(self.default)

        return self.widget

    def getValue(self):
        if self.multiline:
            buf = self.widget.get_buffer()
            return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        else:
            return self.widget.get_text()


class ToggleParameter(Parameter):

    """A parameter representing a binary choice."""

    def __init__(self, default):
        self.require(default, bool)
        self.default = default


class ParameterGroup(object):

    """Manages the parameters required by your script."""

    def __init__(self):
        self.params = OrderedDict()
        self.error = None

    def define(self, name, param):
        if name in self.params:
            raise ValueError("Parameter %s already defined" % name)
        self.params[name] = param

    def makeWidgets(self, container):
        listbox = Gtk.ListBox()
        self.size_group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        for name, param in self.params.items():
            row = Gtk.ListBoxRow()
            box = Gtk.Box(Gtk.Orientation.HORIZONTAL, spacing=6)
            label = Gtk.Label.new("<b><tt>%s</tt></b>" % name)
            widget = param.makeWidget()

            box.show()
            box.set_border_width(5)
            row.add(box)

            label.show()
            label.set_use_markup(True)
            label.set_justify(Gtk.Justification.LEFT)
            box.pack_start(label, False, True, 12)

            self.size_group.add_widget(label)
            box.pack_end(widget, True, True, 12)
            listbox.add(row)

        for child in container.get_children():
            child.destroy()

        container.add(listbox)
        container.show_all()
        self.listbox = listbox

    def getValues(self):
        return {name: param.getValue()
                for name, param in self.params.items()}

    def logError(self, error):
        self.error = error
