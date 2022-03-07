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


import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_foreign("cairo")
from gi.repository import Pango
from gi.repository import PangoCairo
import cmath
import math
import traceback


class Helper(object):

    """Wraps a cairo context in a higher-level API.

    New Primitives:
    - circle
    - elipse
    - round rect
    - center rect
    - center round rect
    - center text
    - polygon
    - vertical and horizontal lines

    Transform Context Managers (so you cannot forget `restore()`):
    - save
    - box

    Wrapper methods which Point and / or Rect objects instead of x/y pairs:
    - moveto
    - lineto
    - curveto

    Debugging features:
    - debug_stroke() - stroke a hairline path using CAIRO_INVERSE
    - debug_fill()   - fill the path using CAIRO_INVERSE
    """

    def __init__(self, cr):
        self.cr = cr
        self.pr = PangoCairo.create_context(cr)

    def circle(self, center, radius):
        self.cr.arc(center.x, center.y, radius, 0, 2 * math.pi)

    def elipse(self, center, width, height):
        with self.save():
            self.cr.translate(center.x, center.y)
            self.cr.scale(1.0, height / width)
            self.circle(Point(0, 0), width)

    def show_text(self, text, font):
        layout = PangoCairo.create_layout(self.cr)
        layout.set_font_description(font)
        layout.set_text(text, -1)
        PangoCairo.show_layout(self.cr, layout)

    def center_text(self, text, font):
        _, _, tw, th, _, _ = self.cr.text_extents(text)
        x, y = self.cr.get_current_point()
        with self.save():
            self.cr.translate(x - tw * 0.5, y + th * 0.5)
            self.cr.move_to(0, 0)
            self.show_text(text, font)

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

    def arc(self, center, rad, start, end):
        self.cr.arc(center.x, center.y, rad, start, end)

    def curve_to(self, a, b, c):
        self.cr.curve_to(a.x, a.y, b.x, b.y, c.x, c.y)

    def hline(self, pos, rect):
        self.cr.move_to(rect.east().x, pos)
        self.cr.line_to(rect.west().x, pos)

    def vline(self, pos, rect):
        self.cr.move_to(pos, rect.north().y)
        self.cr.line_to(pos, rect.south().y)

    def polygon(self, *points, close=True):
        self.move_to(points[0])
        for point in points[1:]:
            self.line_to(point)
        if close:
            self.cr.close()

    def curve(self, close=False, *points):
        raise NotImplementedError()

    def save(self):
        return Save(self.cr)

    def box(self, rect, clip=True):
        return Box(self.cr, rect, clip)

    def _set_source_debug(self):
        self.cr.set_source_rgb(1.0, 1.0, 1.0)
        self.cr.set_operator(cairo.OPERATOR_DIFFERENCE)

    def debug_stroke(self):
        with self.save():
            self._set_source_debug()
            self.cr.identity_matrix()
            self.cr.set_line_width(1.0)
            self.cr.stroke()

    def debug_fill(self):
        with self.save():
            self._set_source_debug()
            self.cr.fill()


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

    @classmethod
    def from_polar(cls, r, theta):
        rect = cmath.rect(r, theta)
        return Point(rect.real, rect.imag)


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
        if self.clip:
            self.cr.rectangle(self.x, self.y, self.width, self.height)
            self.cr.clip()
        self.cr.translate(*self.center)
        return self.bounds

    def __exit__(self, unused1, unused2, unused3):
        self.cr.restore()
 
