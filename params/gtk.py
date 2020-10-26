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

import cmath
from collections import OrderedDict
import math
import time

import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_foreign("cairo")
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk

from controller import ValueController
from helpers import Helper, Rect, Point

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
        self.widget.set_active(self.default)
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

    def getInitEnv(self):
        return {
            '__name__': 'init',
            'cairo': cairo,
            'params': self,
            'Angle': AngleParameter,
            'Choice': ChoiceParameter,
            'Color': ColorParameter,
            'Custom': CustomParameter,
            'Font': FontParameter,
            'Image': ImageParameter,
            'Infinite': InfiniteParameter,
            'Numeric': NumericParameter,
            'Point': PointParameter,
            'Script': ScriptParameter,
            'Table': TableParameter,
            'Text': TextParameter,
            'Toggle': ToggleParameter,
        }

    def getRenderEnv(self, cr, scale, window, stdin):
        return {
            'cr': cr,
            'cairo': cairo,
            'math': math,
            'stdin': stdin,
            'window': window,
            'scale_mm': scale,
            'helpers': Helper(cr),
            'Point': Point,
            'Rect': Rect,
            'time': time.time(),
            '__name__': 'render',
            'params': self.getValues()
        }
