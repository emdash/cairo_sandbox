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

    def circle(self, center, radius):
        self.cr.new_sub_path()
        self.cr.arc(center.x, center.y, radius, 0, 2 * math.pi)

    def elipse(self, center, width, height):
        with self.save():
            self.cr.new_sub_path()
            self.cr.translate(center.x, center.y)
            self.cr.scale(1.0, height / width)
            self.circle(Point(0, 0), width)

    def get_layout(self, text, font):
        layout = PangoCairo.create_layout(self.cr)
        layout.set_font_description(font)
        layout.set_text(text, -1)
        return layout

    def get_layout_rect(self, layout, centered=True):
        rect = layout.get_pixel_extents()[0]
        return Rect(
            Point(rect.x, rect.y),
            rect.width,
            rect.height
        )

    def show_layout(self, layout, centered=True):
        """Render the given layout at the current point.

        If centered is True, then the text is centered on said point.
        Otherwise, the current point is the top-left anchor of the text.
        """
        with self.save():
            if centered:
                rect = layout.get_pixel_extents()[0]
                tw = rect.width
                th = rect.height
                x, y = self.cr.get_current_point()
                self.cr.translate(x - tw * 0.5 - rect.x, y - th * 0.5 - rect.y)
                self.cr.move_to(0, 0)
        PangoCairo.show_layout(self.cr, layout)

    def show_text(self, text, font, centered=True):
        self.show_layout(self.get_layout(text,font), centered)

    # this is now deprecated
    def center_text(self, text, font):
        self.show_text(text, font, centered=True)

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
            # these two things give us a hairline.
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
    def __eq__(self, o):
        return isinstance(o, Point) and (self.x, self.y) == (o.x, o.y)
    def __repr__(self):       return "(%g,%g)" % (self.x, self.y)
    def __iter__(self):       yield  self.x ; yield self.y
    def __hash__(self):       return hash((self.x, self.y))
    def __bool__(self):       return False

    def len(self): return math.sqrt(self.x ** 2 + self.y ** 2)

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

    def guides(self, vertical, horizontal):
        return Guides(self, vertical, horizontal)


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
        self.path = None

    def __enter__(self):
        self.cr.save()
        if self.clip:
            self.path = self.cr.copy_path()
            self.cr.rectangle(self.x, self.y, self.width, self.height)
            self.cr.clip()
        self.cr.translate(*self.center)
        return self.bounds

    def __exit__(self, unused1, unused2, unused3):
        self.cr.restore()
        if self.clip:
            self.cr.append_path(self.path)


class Guides:

    """Slice a rectangle horizontally and vertically.

    The given rectangle is subdivided by a set of horizontal and
    vertical guide lines. The guide lines are interpreted as a
    percentage of the Rect's total width or height.

    This defines a set of intersection points within the rectangle as
    well as a cet of "cells" within the rectangle between each line.

    The first and most obvious use case is to create tabular
    layouts. One can refer to the logical position of a column or row,
    independent of its exact position or offset.

    A less obvious use case is defining layout lines or "skeletal"
    geometry. In art and science, one often finds that certain rules of
    proportions should be observed, e.g: golden ratio, rule of thirds,
    human proportions, etc.

    Intersection points and cells are identified by a 2D index. Consider
    the following example:

      g = Guides(
         Rect(Point(0, 0), 100, 100)),
         (0.25, 0.5, 0.75),
         (1/3, 0.75)
      )

    For points, (0, 0) identifies the northwest corner of the enclosing
    Rect. (1, 1) identifies the intersection of the first two
    user-supplied guide lines:

      g.intersection(0, 0) # Point(-50, -50)
      g.intersection(1, 0) # Point(-25, -50)
      g.intersection(1, 1) # Point(-25, -16.666...)

    For cells, (0, 0) identifies the cell whose northwest corner is
    g.intersection(0, 0), and whose southeast corner is
    g.intersection(1, 1).

    When you want to reference the point at which two guides meet, use the
    `intersection()` method. When you want to reference the space
    *between* guides, use the `cell()` method.

    If you want to refer to and entire row or column, use the `row()` or
    `col()` methods.

    Note: guide positions are "absolute" positions from the top or left
    edge. In order for indexing to work correctly, horizontal and
    vertical guide positions are sorted in ascending order. To avoid
    confusion, always specify guide positions in ascending order.
    """

    def __init__(self, rect, vertical, horizontal):
        self.rect = rect
        self.horizontal = (
            0,
            *(rect.height * h for h in sorted(horizontal)),
            rect.height
        )
        self.vertical = (
            0,
            *(rect.width * v for v in sorted(vertical)),
            rect.width
        )

    def intersection(self, v, h):
        """Get the intersection point for the given 2d index."""
        return self.rect.northwest() + Point(self.vertical[v], self.horizontal[h])

    def cell(self, v, h):
        """Get the table cell from the given 2d index."""
        tl = self.intersection(v, h)
        br = self.intersection(v + 1, h + 1)
        size = br - tl
        return Rect.from_top_left(tl, size.x, size.y)

    def column(self, h):
        tl = self.intersection(h, 0)
        tr = self.intersection(h + 1, 0)
        size = tr - tl
        return Rect.from_top_left(tl, size.x, self.rect.height)

    def row(self, v):
        tl = self.intersection(0, v)
        bl = self.intersection(0, v + 1)
        size = bl - tl
        return Rect.from_top_left(tl, self.rect.width, size.y)

    def draw(self, helpers, show_outline=True):
        """Add the guide to the current path, but do not fill or stroke.

        Use this method if you want control over how the guides are
        displayed.
        """
        if show_outline:
            helpers.rect(self.rect)
        for h in self.horizontal:
            helpers.hline(h, self.rect)
        for v in self.vertical:
            helpers.vline(v, self.rect)

    # TBD: add show_indices option
    def debug(self, helpers, show_outline=True):
        """Render the guidelines using debug_stroke.

        Use this method if you want to make sure the guide lines are
        legible against anything previously drawn to the canvas.
        """
        self.draw(helpers, show_outline)
        helpers.debug_stroke()
