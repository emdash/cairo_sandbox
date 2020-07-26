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
import cmath
import math
import traceback


import gi
gi.require_version("Gtk", "3.0")
gi.require_foreign("cairo")
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk


class CursorState(object):
    """ABC For the Cursor State Machine"""

    def button_press(self, event):
        raise NotImplementedError()

    def button_release(self, event):
        raise NotImplementedError()

    def mouse_move(self, event):
        raise NotImplementedError()

    def dispatch(self, callbacks):
        raise NotImplementedError()


class Hover(CursorState):

    def __init__(self, pos):
        self.pos = pos

    def button_press(self, event):
        return DragBegin(Point(event.x, event.y), self.pos)

    def button_release(self, event):
        return Hover(Point(event.x, event.y))

    def mouse_move(self, event):
        return Hover(Point(event.x, event.y))

    def dispatch(self, callbacks):
        return callbacks.hover(self)


class Click(Hover):

    def dispatch(self, callbacks):
        return callbacks.click(self)


class DragBegin(CursorState):

    def __init__(self, pos, origin):
        self.pos = pos
        self.origin = origin
        self.rel = self.pos - self.origin

    def button_press(self, event):
        return Hover(Point(event.x, event.y))

    def button_release(self, event):
        return Click(Point(event.x, event.y))

    def mouse_move(self, event):
        return DragMove(Point(event.x, event.y), self.origin)

    def dispatch(self, callbacks):
        return callbacks.begin(self)


class DragEnd(CursorState):

    drag_threshold = 1.0

    def __init__(self, pos, origin):
        self.pos = pos
        self.origin = origin
        self.rel = self.pos - self.origin

    def button_press(self, event):
        return Hover(Point(event.x, event.y))

    def button_release(self, event):
        if rel.dist() > self.drag_threshold:
            return DragEnd(Point(event.x, event.y), self.origin)
        else:
            return Click(Point(event.x, event.y))

    def mouse_move(self, event):
        return Hover(Point(event.x, event.y))

    def dispatch(self, callbacks):
        return callbacks.drop(self)


class DragMove(CursorState):

    def __init__(self, pos, origin):
        self.pos = pos
        self.origin = origin
        self.rel = self.pos - self.origin

    def button_press(self, event):
        return Hover(Point(event.x, event.y))

    def button_release(self, event):
        return DragEnd(Point(event.x, event.y), self.origin)

    def mouse_move(self, event):
        return DragMove(Point(event.x, event.y), self.origin)

    def dispatch(self, callbacks):
        return callbacks.drag(self)


class DragController(object):

    """Factor out common drag-and-drop state machine pattern.

    This interface is simpler than the platform drag-and-drop
    interface, while losing little of its power.

    The key concept we add is the `rel` parameter to the currsor state
    object. Correctly calculating `rel` parameter requires capturing
    some state at mouse-down which is preserved through the drag
    interaction.

    `callbacks` is an object which provides the following methods:
    - hover
    - begin
    - drag
    - drop

    """

    def __init__(self, widget, callbacks):
        """Creates a DragController bound to `widget.`
        """
        self.callbacks = callbacks
        self.cursor = Hover(Point(0, 0))
        widget.set_events(Gdk.EventMask.EXPOSURE_MASK
		          | Gdk.EventMask.LEAVE_NOTIFY_MASK
		          | Gdk.EventMask.BUTTON_PRESS_MASK
		          | Gdk.EventMask.BUTTON_RELEASE_MASK
		          | Gdk.EventMask.POINTER_MOTION_MASK
		          | Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        widget.connect('button-press-event', self.button_press)
        widget.connect('button-release-event', self.button_release)
        widget.connect('motion-notify-event', self.mouse_move)

    def button_press(self, widget, event):
        self.cursor = self.cursor.button_press(event)
        if self.cursor.dispatch(self.callbacks):
            widget.queue_draw()

    def button_release(self, widget, event):
        self.cursor = self.cursor.button_release(event)
        if self.cursor.dispatch(self.callbacks):
            widget.queue_draw()

    def mouse_move(self, widget, event):
        self.cursor = self.cursor.mouse_move(event)
        if self.cursor.dispatch(self.callbacks):
            widget.queue_draw()


# XXX: better name for this.
class ValueController(object):

    """A special-case of DragController which binds a single value.

    Users should supply a pair of callbacks:

    - begin(cursor): the drag is beginning, cached any state if necessary.
    - updateValue(cursor): update the value based on current cursor state.
    """

    def __init__(self, widget, callbacks):
        self.dc = DragController(widget, self)
        self.callbacks = callbacks
        self.begin = callbacks.begin

    def hover(self, cursor):
        pass

    def drag(self, cursor):
        self.callbacks.updateValue(cursor)
        return True

    def drop(self, cursor):
        self.callbacks.updateValue(cursor)
        return True

    def click(self, click):
        return True


class Helper(object):

    """Provide useful methods not available in the standard cairo API."""

    def __init__(self, cr):
        self.cr = cr

    def circle(self, center, radius):
        self.cr.arc(center.x, center.y, radius, 0, 2 * math.pi)

    def elipse(self, center, width, height):
        with self.save():
            self.cr.translate(center.x, center.y)
            self.cr.scale(1.0, height / width)
            self.circle(Point(0, 0), width)

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


class Parameter(object):

    """A uniform interface for creating live-adjustable parameters."""

    def require(self, value, allowed_types):
        """Raise an error if `value` is not one of `allowed_types`.

        `allowed_types` may be a tuple or a single type.
        """

        if not isinstance(value, allowed_types):
            raise TypeError("Expected one of %s, got %r." % (
                ", ".join(repr(t) for t in allowed_types),
                value
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

    """A numeric value clamped between 0 and 2 * math.pi.

    The value will be the angle between the mouse position at
    mousedown and the current mouse position.
    """

    def __init__(self, default, format="%.2f"):
        self.require(default, (float, int, None))
        self.default = default
        self.adjustment = Gtk.Adjustment(
            0,
            0,
            math.pi * 2,
            1/3600.0)
        self.saved_value = default
        self.adjustment.set_value(default)
        self.format = format
        self.label = None
        self.vc = None

    def makeWidget(self):
        entry = Gtk.SpinButton.new(self.adjustment, 1/3600.0, 3)

        # XXX: Hack alert
        ParameterGroup.entry_group.add_widget(entry)

        widget = Gtk.DrawingArea()
        widget.set_size_request(30, 30)
        widget.connect('draw', self.draw)
        self.vc = ValueController(widget, self)
        self.label = Gtk.Label(str(self.adjustment.get_value()))
        box = Gtk.Box(Gtk.Orientation.HORIZONTAL)
        box.pack_start(entry, False, False, 12)
        box.pack_start(widget, False, False, 12)
        box.pack_end(self.label, False, False, 12)
        return box

    def begin(self, cursor):
        self.saved_value = self.adjustment.get_value()

    def getValue(self):
        return self.adjustment.get_value()

    def updateValue(self, cursor):
        # (ab)use complex built-in to compute the angle of the mouse.
        angle = cmath.polar(complex(cursor.pos.x, cursor.pos.y))[1]
        value = (angle + self.saved_value) % (2 * math.pi)
        self.adjustment.set_value(value)
        self.label.set_text(self.format % value)

    def draw(self, widget, cr):
        helper = Helper(cr)
        alloc = widget.get_allocation()
        window = Rect.from_top_left(Point(0, 0), alloc.width, alloc.height)
        with helper.box(window.inset(5), clip=False) as bounds:
            radius = min(bounds.width, bounds.height) * 0.5
            helper.circle(bounds.center, radius)
            cr.set_line_width(2.5)
            cr.stroke()
            cr.rotate(self.adjustment.get_value())
            helper.circle(Point(radius/2, 0), radius/4)
            cr.fill()


class ChoiceParameter(Parameter):

    """A parameter representing a choice of alternatives.
    """

    def __init__(self, alternatives, default, with_entry=False):
        # XXX: should be any seq
        self.require(alternatives, (tuple, list, dict))
        self.require(with_entry, bool)
        self.alternatives = alternatives

        if not default in alternatives:
            raise ValueError("Default must be one of the alternatives")

        self.with_entry = with_entry

        # Type checking for the dict case
        if isinstance(alternatives, dict):
            items = iter(alternatives.values())
            t = type(items.__next__())
            self.value_col = 0

            for key in alternatives:
                self.require(key, str)

            if not all(isinstance(v, t) for v in items):
                raise TypeError("All alternatives must be the same type")

            self.store = Gtk.ListStore(str)

            for (i, (k, v)) in enumerate(alternatives.items()):
                self.store.append([k])
                if k == default:
                    self.default_row = i
        else:
            self.value_col = 1
            t = type(alternatives[0])

            if not all(isinstance(v, t) for v in alternatives):
                raise TypeError("All alternatives must be the same type")

            self.store = Gtk.ListStore(t, int)

            for i, item in enumerate(alternatives):
                self.store.append((item, i))
                if item == default:
                    self.default_row = i

    def makeWidget(self):
        if self.with_entry:
            self.widget = Gtk.ComboBox.new_with_entry()
            self.widget.set_entry_text_column(0)
        else:
            self.widget = Gtk.ComboBox.new()
            cr = Gtk.CellRendererText()
            self.widget.pack_start(cr, True)
            self.widget.add_attribute(cr, "text", 0)
        self.widget.set_model(self.store)
        self.widget.set_active(self.default_row)

        return self.widget

    def getValue(self):
        i = self.widget.get_active_iter()
        if i is not None:
            if isinstance(self.alternatives, dict):
                return self.alternatives[self.store[i][self.value_col]]
            else:
                return self.alternatives[self.store[i][self.value_col]]
        else:
            return None


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

    pass


class FontParameter(Parameter):

    """An easy way to chose a specific font."""

    # TBD: When we support Pango for text, revisit this control.

    def __init__(self, default="monospace", use_pango=False):
        self.require(default, (str, type(None)))
        self.require(use_pango, bool)
        if (use_pango):
            raise NotImplementedError()
        self.use_pango = use_pango
        self.default = default
        self.value = default
        self.widget = None

    def makeWidget(self):
        if self.default is not None:
            self.widget = Gtk.FontButton.new_with_font(self.default)
        else:
            self.widget = Gtk.FontButton.new()
        self.widget.set_use_font(True)
        self.widget.set_use_size(False)
        self.widget.set_show_size(False)
        self.widget.connect("font-set", self.update)
        return self.widget

    def update(self, *unused):
        self.value = self.widget.get_font().split()[0]

    def getValue(self):
        return self.value


class ImageParameter(Parameter):

    """A convenient way to load an image from disk.

    If loading succeeds, the will be converted to a cairo.ImagePattern.
    """

    def __init__(self, default=None):
        # Default can be a fallback pattern, or a path to an image.
        self.require(default, (str, cairo.Pattern, type(None)))
        self.default = default
        self.value = default

    def makeWidget(self):
        self.widget = Gtk.FileChooserButton().new(
            "Choose Image",
            Gtk.FileChooserAction.OPEN)

        if isinstance(self.default, str):
            self.widget.select_filename(default)

        self.widget.connect("file-set", self.update)
        return self.widget

    def update(self, *unused):
        path = self.widget.get_filename()
        try:
            self.value = cairo.SurfacePattern(
                cairo.ImageSurface.create_from_png(path))
        except BaseException:
            traceback.print_exc()
            self.value = self.default

    def getValue(self):
        return self.value


class InfiniteParameter(Parameter):

    """A scalar value that is not constrained to a finite interval."""

    def __init__(self, default, rate=0.125, format="%.2f"):
        self.require(default, (float, int, None))
        self.default = default
        self.value = default
        self.saved_value = default
        self.rate = rate
        self.format = format
        self.label = None
        self.vc = None

    def makeWidget(self):
        entry = Gtk.Entry()
        # XXX: Hack alert
        ParameterGroup.entry_group.add_widget(entry)

        widget = Gtk.DrawingArea()
        widget.set_size_request(30, 30)
        widget.connect('draw', self.draw)
        self.vc = ValueController(widget, self)
        self.label = Gtk.Label(str(self.value))
        box = Gtk.Box(Gtk.Orientation.HORIZONTAL)
        box.pack_start(entry, False, False, 12)
        box.pack_start(widget, False, False, 12)
        box.pack_end(self.label, False, False, 12)
        return box

    def begin(self, cursor):
        self.saved_value = self.value

    def getValue(self):
        return self.value

    def updateValue(self, cursor):
        value = self.saved_value - self.rate * cursor.rel.y
        self.value = value
        self.label.set_text(self.format % value)

    def draw(self, widget, cr):
        helper = Helper(cr)
        alloc = widget.get_allocation()
        window = Rect.from_top_left(Point(0, 0), alloc.width, alloc.height)
        with helper.box(window.inset(5), clip=False) as bounds:
            radius = min(bounds.width, bounds.height) * 0.5
            helper.circle(bounds.center, radius)
            cr.set_line_width(2.5)
            cr.stroke()
            cr.rotate(self.value)
            helper.circle(Point(radius/2, 0), radius/4)
            cr.fill()


class NumericParameter(Parameter):

    """A scalar numeric value, with a finite range."""

    def __init__(self, lower, upper, step=1/128.0, default=0.5):
        allowed = (int, float, complex)
        self.require(lower, allowed)
        self.require(upper, allowed)
        self.require(default, allowed)
        self.lower = lower
        self.upper = upper
        self.step = step
        self.default = default
        self.adjustment = None

    def makeWidget(self):
        self.adjustment = Gtk.Adjustment(
            self.default,
            self.lower,
            self.upper,
            self.step)
        scale = widget = Gtk.Scale.new(
            Gtk.Orientation.HORIZONTAL,
            self.adjustment)
        scale.set_draw_value(True)
        entry = Gtk.SpinButton.new(self.adjustment, self.step, 3)

        # XXX: Hack alert
        ParameterGroup.entry_group.add_widget(entry)

        ret = Gtk.Box(Gtk.Orientation.HORIZONTAL)
        ret.pack_start(entry, False, False, 12)
        ret.pack_start(scale, True, True, 12)
        ret.show()
        return ret

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

    def makeWidget(self):
        self.widget = Gtk.CheckButton()
        self.widget.set_active(True)
        return self.widget

    def getValue(self):
        return self.widget.get_active()


class ParameterGroup(object):

    """Manages the parameters required by your script."""

    entry_group = None

    def __init__(self):
        self.params = OrderedDict()
        self.resolution = 640, 480

    def define(self, name, param):
        """Define a new parameter for later use in the a user script."""

        if name in self.params:
            raise ValueError("Parameter %s already defined" % name)
        self.params[name] = param

    def makeWidgets(self, container):
        """Create a widget for each parameter, adding them into `container`.

        All of the widgets are added to a child container. If
        container alrady contains widget, it will be removed.

        Currently this means that all the existing widgets will lose
        their values, but since we cannot know that the set of
        paramers has not changed, this is the simplest and sanest
        approach.

        """
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)

        self.size_group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        # XXX: a bit of hack for widgets that want to coordinate
        # sizing their left-most child widget.
        #
        # this is stored as a class property to avoid having to pass
        # it down to makeWidget. It needs to be replaced with each
        # generation of parameters to avoid leaking the widgets.
        ParameterGroup.entry_group = Gtk.SizeGroup(
            Gtk.SizeGroupMode.HORIZONTAL)

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
        """Get the current value for each parameter, as dict."""
        return {name: param.getValue()
                for name, param in self.params.items()}

    def setResolution(self, x, y):
        """Set the resolution of the drawing area.

        This will be used in a subsequent `set_size_request_call` on
        the underlying output widget.

        This method doesn't really belong in this class, but it is the
        most convenient place to put it for the time being.

        """
        self.resolution = x, y
