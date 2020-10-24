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

"""Text-based parameter implementations."""

import cmath
from collections import OrderedDict
import math
import time
import os

import cairo
from controller import ValueController
from helpers import Helper, Rect, Point


class Parameter(object):

    """A uniform interface for creating parameters from the environment."""

    def require(self, value, allowed_types):
        """Raise an error if `value` is not one of `allowed_types`.

        `allowed_types` may be a tuple or a single type.
        """

        if not isinstance(value, allowed_types):
            raise TypeError("Expected one of %s, got %r." % (
                ", ".join(repr(t) for t in allowed_types),
                value
            ))

    def parse(self, text):
        raise NotImplementedError


class AngleParameter(Parameter):

    """A numeric value clamped between 0 and 2 * math.pi.

    The value will be the angle between the mouse position at
    mousedown and the current mouse position.
    """

    def __init__(self, default, format="%.2f"):
        self.require(default, (float, int, None))
        self.default = default

    def parse(self, text):
        return float(text)


class ChoiceParameter(Parameter):

    """A parameter representing a choice of alternatives.
    """

    def __init__(self, alternatives, default, with_entry=False):
        # XXX: should be any seq
        self.require(alternatives, (tuple, list, dict))
        self.require(with_entry, bool)
        self.alternatives = alternatives

        if isinstance(alternatives, dict):
            self.default = alternatives[default]
        else:
            self.default = alternatives.index(default)

        if not default in alternatives:
            raise ValueError("Default must be one of the alternatives")

        self.with_entry = with_entry

    def parse(self, text):
        if text not in self.alternatives:
            raise ValueError(
                "{} is not one of {}".format((text, self.alternatives)))
        return self.alternatives[text]


# TBD: images, gradients, stipples, etc.
class ColorParameter(Parameter):

    """An RGBA Color value."""

    def __init__(self, r=0, g=0, b=0, a=1.0):
        self.require(r, (int, float))
        self.require(g, (int, float))
        self.require(b, (int, float))
        self.require(a, (int, float))
        self.default = cairo.SolidPattern(r, g, b, a)

    def parse(self, text):
        # TBD, other color formats
        if not len(text) == 8:
            raise ValueError("Could not parse as color: " + text)

        a = int(text[0:2], 16) / 0xFF
        r = int(text[2:4], 16) / 0xFF
        g = int(text[4:6], 16) / 0xFF
        b = int(text[6:8], 16) / 0xFF
        return cairo.SolidPattern(r, g, b, a)


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

    def parse(self, text):
        ## TBD, check font exits
        return text


class ImageParameter(Parameter):

    """A convenient way to load an image from disk.

    If loading succeeds, the will be converted to a cairo.ImagePattern.
    """

    def __init__(self, default=None):
        # Default can be a fallback pattern, or a path to an image.
        self.require(default, (str, cairo.Pattern, type(None)))
        self.default = default

    def parse(self, text):
        return cairo.SurfacePattern(cairo.ImageSurface.create_from_png(text))


class InfiniteParameter(Parameter):

    """A scalar value that is not constrained to a finite interval."""

    def __init__(self, default, rate=0.125, format="%.2f"):
        self.require(default, (float, int, None))
        self.default = default

    def parse(self, text):
        return type(self.default)(text)


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

    def parse(self, text):
        value = type(self.default)(text)
        if self.lower <= value <= self.upper:
            return value
        else:
            raise ValueError(
                "{} not in range [{}, {}]".format(value, self.lower, self.upper)
            )


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
        raise NotImplementedError


class TableParameter(Parameter):

    """An arbitrary of values, which may themelves be tuples."""

    def __init__(self, row_type, default=None):
        self.require(row_type, (list, tuple))
        for item in row_type:
            self.require(item, (str, int, float, long, Point, Color))
        self.row_type = row_type
        self.default = default
        raise NotImplementedError


class TextParameter(Parameter):

    """An arbitrary text string."""

    def __init__(self, default=None, multiline=False):
        self.require(default, (str, None))
        self.require(multiline, bool)
        self.multiline = multiline
        self.default = default

    def parse(self, text):
        return text


class ToggleParameter(Parameter):

    """A parameter representing a binary choice."""

    def __init__(self, default):
        self.require(default, bool)
        self.default = default

    def parse(self, text):
        if text == "true":
            return True
        elif text == "false":
            return False

        raise ValueError("Could not parse {} as bool".format(text))


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

    def getValues(self):
        """Get the current value for each parameter, as dict."""
        return {
            name: self.getParamValue(name, param)
            for name, param in self.params.items()
        }

    def getParamValue(self, name, param):
        if name in os.environ:
            return param.parse(os.environ[name])
        else:
            return param.default

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
