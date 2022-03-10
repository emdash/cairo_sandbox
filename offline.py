#! /usr/bin/python3
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
#
# Heavily inspired by "surface.py" by Sean Vig, in the pywayland
# examples directory. Adapted and expanded for this use-case.


"""Offline rendering of cairo_sandbox scripts.

Renders the given cairo_sandbox script to a file or stdout as
determined by the given options.

Intended mainly for batch processing workflows (documentation, unit
tests, etc).

The following modes of operation are supported:
- nostdin    -- do not read params from stdin. all params must be
                supplied via the environment. implies oneshot.
- oneshot    -- render a single frame from stdin.
- continuous -- overwrite the same output file.
- sequence   -- render each frame as a separate file in the given directory.
- slideshow  -- render each frame as a separate page in the given file
                (ps, pdf, and SVG only).
"""

# TBD: render to .mp4 via gstreamer?

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_foreign("cairo")
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango
gi.require_version("PangoCairo", "1.0");
from gi.repository import PangoCairo
import cairo

import math
import json
import os
import threading
import time
import sys
import argparse

from helpers import Rect, Point
from script import Script
import params.text as params
import argparse


def pt_to_pixel(pts, dpi):
    return int(pts * dpi / 72.0)

def mm_to_in(mm):
    return mm / 25.4

def in_to_pt(inches):
    return inches * 72

def parse_unit(value):
    # TBD: distinguish between:
    # - no unit: assume points.
    # - mm: convert to inch, then convert points
    # - in: convert to to points.
    # - pt: do not convert.
    if value.endswith("mm"):
        return in_to_pt(mm_to_in(float(value[:-2])))
    elif value.endswith("in"):
        return in_to_pt(float(value[:-2]))
    elif value.endswith("pt"):
        return float(value[:-2])
    else:
        return float(value)


class UserError(BaseException):
    pass


class SurfaceWrapper:
    """Abstract the diffeent output formats cairo supports.

    There are some wierd asymmetries in the cairo API. This family of
    classes attempts to smooth this over.

    In particular, there's no obvious way to create a "blank" PNG
    surface for painting. Rather, one creates an ImageSurface and writes
    it as a .png file.

    While we're here, we also abstract over the different supported
    modes of operation.
    """

    @classmethod
    def from_args(self, args):
        fmt = args.format
        if   fmt == "png": return PngSurfaceWrapper(args)
        elif fmt == "ps":  return PsSurfaceWrapper(args)
        elif fmt == "pdf": return PdfSurfaceWrapper(args)
        elif fmt == "svg": return SvgSurfaceWrapper(args)

    def render(self, script):
        try:
            self.cr.save()
            self.cr.set_source_rgba(0, 0, 0, 0)
            self.cr.paint()
            script.run(self.cr, self.scale, self.window)
        finally:
            self.cr.restore()

    def nostdin(self, script):
        try:
            self.render(script)
        finally:
            self.write()

    def oneshot(self, script, reader):
        try:
            reader.update(sys.stdin.readline())
            self.render(script)
        finally:
            self.write()

    def continuous(self, script, reader):
        for line in sys.stdin():
            try:
                reader.update(line)
                self.render(script)
            finally:
                self.write()

    def sequence(self, script, reader):
        for (i, line) in enumerate(sys.stdin()):
            reader.update(line)
            try:
                self.render(script)
            finally:
                self.write()
            self.next_image(i)

    def slideshow(self, script, reader):
        try:
            for line in sys.stdin():
                reader.update(line)
                self.render(script)
                self.next_page()
        finally:
            self.write()

    def next_image(self, index):
        raise NotImplemented

    def next_page(self):
        """Defined in supported subclasses"""
        raise NotImplemented

    def write(self):
        """Defined by all subclasses."""
        raise NotImplemented


class PngSurfaceWrapper(SurfaceWrapper):
    def __init__(self, args):
        width, height = args.size

        self.surface = cairo.ImageSurface(cairo.Format.ARGB32, int(width), int(height))
        self.window = Rect.from_top_left(Point(0, 0), width, height)
        self.scale = Point(args.dpi / 25.4, args.dpi / 25.4)
        self.cr = cairo.Context(self.surface)

        if args.output is None:
            # The only reason for this is that `cairo_surface_write_to_png_stream`
            # is not exposed by pycairo.
            raise UserError("PNG does not support streaming to stdout.")
        else:
            if args.mode == "sequence":
                self.output_dir = args.output
                self.index = -1
                os.mkdir(output_dir)
                self.next_image()
            else:
                self.output = args.output

    def write(self):
        self.surface.write_to_png(self.output)

    def next_image(self):
        self.index += 1
        self.output = os.path.join(self.output_dir, "%d.png" % self.index)

    def next_page(self):
        raise UserError("The PNG format does not support slideshows.")


class DummyReader:
    """Dummy reader for single-threaded operation.
    The wayland and gtk runners process data from stdin on a separate
    thread to avoid blocking the mainloop. We don't need to do this
    here. We just need an object instance to hold the env property,
    which we update "in place".
    """

    # TBD: the need for this is a code smell. Some refactoring of `Script` and `Params` is
    # in order.

    def __init__(self):
        self.env = {}

    def update(line):
        self.env = json.loads(line)


if __name__ == "__main__":
    desc = "Generate stand-alone images from cairo_sandbox scripts."
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument(
        "-m", "--mode",
        help="Specifies output mode",
        metavar="MODE",
        choices=("nostdin", "oneshot", "continuous", "sequence", "slideshow"),
        default="nostdin"
    )

    parser.add_argument(
        "-f", "--format",
        help="Output file format",
        metavar="FMT",
        choices=("png", "ps", "pdf", "svg", "script"),
        required=True
    )

    parser.add_argument(
        "-o", "--output",
        help="The output file path (defaults to `stdout`)",
        metavar="FILE",
        type=str
    )

    parser.add_argument(
        "-s", "--size",
        help="The width and height of the output image in physical units",
        nargs=2,
        type=parse_unit,
        required=True
    )

    parser.add_argument(
        "-d", "--dpi",
        help="Override default DPI (PNG only).",
        metavar="DPI",
        default=96,
        type=int,
    )

    # TBD: we can't support this yet.
    # parser.add_argument(
    #     "-p", "--param",
    #     help="Specify the value of a parameter..",
    #     nargs=2,
    #     dest="params",
    #     action="append",
    # )

    parser.add_argument(
        "script",
        help="Path to the script to execute"
    )

    args = parser.parse_args(sys.argv[1:])
    reader = DummyReader()
    script = Script(args.script, reader, render_tb=False, halt_on_exc=True)
    script.reload(params.ParameterGroup())
    wrapper = SurfaceWrapper.from_args(args)

    try:
        if   args.mode == "nostdin":    wrapper.nostdin(script)
        elif args.mode == "oneshot":    wrapper.oneshot(script,    reader)
        elif args.mode == "continuous": wrapper.continuous(script, reader)
        elif args.mode == "sequence":   wrapper.sequence(script,   reader)
        elif args.mode == "slideshow":  wrapper.slideshow(script,  reader)
    except UserError as e:
        print(e)
        exit(-1)
