#!/usr/bin/python3
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

# TODOS:
# - allow for keyboard interrupt to work, plus some way for graceful exit.
# - do we need explicit double buffering, or does wayland do this?
# - damage region optimizations.


"""Stand-alone runner for pywayland."""


import math
import mmap
import json
import os
import threading
import time
import sys

import cairo

import script
from helpers import Rect, Point
import params.text as params


from pywayland.client import Display
from pywayland.protocol.wayland import WlCompositor, WlShell, WlShm, WlOutput
from pywayland.utils import AnonymousFile


def stride_for_format(width, format_):
    """Return the stride length in bytes for given pixel width and format."""

    if format_ == WlShm.format.argb8888.value:
        return 4 * width
    elif format_ == WlShm.format.xrgb8888.value:
        return 4 * width
    elif format_ == WlShm.format.rgb565.value:
        return 2 * width
    else:
        raise ValueError("incompatible format: {}".format(repr(format_)))    


def wayland_format_to_cairo_format(format_):
    """Return the Cairo.Format value for the given WlShm.format."""

    if format_ == WlShm.format.argb8888.value:
        return cairo.Format.ARGB32
    elif format_ == WlShm.format.xrgb8888.value:
        return cairo.Format.RGB24
    elif format_ == WlShm.format.rgb565.value:
        return cairo.Format.RGB16_565
    else:
        raise ValueError("incompatible format: {}".format(repr(format_)))


class Window(object):

    """Wrapper around pywayland window which configures painting."""

    def __init__(self, client, width, height, on_paint=None):
        self.width = width
        self.height = height
        self.format = wayland_format_to_cairo_format(client.best_format())
        self.on_paint = on_paint

        self.surface = client.compositor.create_surface()
        
        self.shell_surface = client.shell.get_shell_surface(self.surface)
        self.shell_surface.dispatcher["ping"] = self.ping_handler
        self.set_fullscreen()

        self.frame_callback = self.surface.frame()
        self.frame_callback.dispatcher["done"] = self.redraw

        self.shm_data, self.buffer = client.create_buffer(self.width, self.height)
        self.cairo_surface = self.create_cairo_surface()
        self.cr = cairo.Context(self.cairo_surface)
        self.surface.attach(self.buffer, 0, 0)
        self.surface.commit()

        self.redraw(self.frame_callback, 0, destroy_callback=False)

    def set_fullscreen(self):
        self.shell_surface.set_fullscreen(0, 0, None)

    def set_toplevel(self):
        self.shell_surface.set_toplevel()

    def ping_handler(self, shell_surface, serial):
        shell_surface.pong(serial)
        print("pinged/ponged")

    def create_cairo_surface(self):
        assert self.shm_data is not None
    
        return cairo.ImageSurface.create_for_data(
            self.shm_data,
            self.format,
            self.width,
            self.height,
            stride_for_format(self.width, self.format))
    
    def redraw(self, callback, time, destroy_callback=True):
        if destroy_callback:
            callback._destroy()
    
        self.paint(self.cr)
        self.surface.damage(0, 0, self.width, self.height)
    
        callback = self.surface.frame()
        callback.dispatcher["done"] = self.redraw
    
        self.surface.attach(self.buffer, 0, 0)
        self.surface.commit()
    
    def paint(self, cr):
        try:
            self.cr.save()
            self.cr.set_source_rgb(1.0, 1.0, 1.0)
            self.cr.paint()
            self.on_paint(cr)
        finally:
            self.cr.restore()


class WaylandClient(object):

    """High level interface for wayland client."""

    preferred_formats = (
        WlShm.format.argb8888,
        WlShm.format.xrgb8888,
        WlShm.format.rgb565
    )

    def __init__(self):
        self.display = Display()
        self.connected = False
        self.formats = set()

        # initialize these to None
        self.compositor = None
        self.shell = None
        self.registry = None

        self.connect()

    def ensure_connected(self):
        if not self.connected:
            raise RuntimeError("Not connected");

    def connect(self):
        assert not self.connected
        self.width_mm = None
        self.height_mm = None

        self.display.connect()
        print("connected to display")

        registry = self.display.get_registry()
        registry.dispatcher["global"] = self.handler
        self.display.dispatch(block=True)
        self.display.roundtrip()

        if self.compositor is None:
            raise RuntimeError("no compositor found")
        elif self.shell is None:
            raise RuntimeError("no shell found")
        elif self.shm is None:
            raise RuntimeError("no shm found")

        while self.width_mm is None:
            self.display.dispatch(block=True)
            self.display.roundtrip()

        self.connected = True

    def create_window(self, width, height, on_paint):
        self.ensure_connected()
        return Window(self, width, height, on_paint)
        
    def handler(self, registry, id_, interface, version):
        if interface == "wl_compositor":
            self.compositor = registry.bind(id_, WlCompositor, version)
        elif interface == "wl_shell":
            self.shell = registry.bind(id_, WlShell, version)
        elif interface == "wl_shm":
            self.shm = registry.bind(id_, WlShm, version)
            self.shm.dispatcher["format"] = self.shm_format_handler
        elif interface == "wl_output":
            self.output = registry.bind(id_, WlOutput, version)
            self.output.dispatcher["geometry"] = self.geometry_handler
            self.output.dispatcher["mode"] = self.mode_handler
        else:
            print("Unhandled proxy:", interface)

    def run(self):
        self.ensure_connected()
        while self.display.dispatch(block=True) != -1:
            pass
        time.sleep(1)
        display.disconnect()

    def shm_format_handler(self, unused, format_):
        self.formats.add(WlShm.format(format_))

    def geometry_handler(self, unused, x, y, width, height, *wtf):
        self.width_mm = width
        self.height_mm = height
        print(wtf)

    def mode_handler(self, unused, flags, width, height, refresh):
        self.mode_flags = flags
        self.width_pixels = width
        self.height_pixels = height
        self.refresh_mhz = refresh
        print("Output Mode: {}x{}@{}".format(width, height, refresh))

    def create_buffer(self, width, height):
        stride = stride_for_format(width, client.best_format())
        size = stride * height

        with AnonymousFile(size) as fd:
            shm_data = mmap.mmap(
                fd,
                size,
                prot=mmap.PROT_READ | mmap.PROT_WRITE,
                flags=mmap.MAP_SHARED)
            pool = client.shm.create_pool(fd, size)
            buff = pool.create_buffer(
                0,
                width,
                height,
                stride,
                WlShm.format.argb8888.value)
            pool.destroy()
            return shm_data, buff

    def best_format(self):
        for f in self.preferred_formats:
            if f in self.formats:
                return f
        raise ValueError("No supported formats!")


class ReaderThread(threading.Thread):

    env = {}
    daemon = True

    def run(self):
        while True:
            self.env = json.loads(sys.stdin.readline())


def on_paint(cr):
    scale = Point(
        client.width_pixels / client.width_mm,
        client.height_pixels / client.height_mm)
    script.run(cr, scale, window)


if __name__ == "__main__":

    reader = ReaderThread()
    script = script.Script(sys.argv[1], reader)
    params = params.ParameterGroup()
    script.reload(params)

    # TBD: this only works for a static output, it will break if the
    # output resoluation changes. That's okay for this use-case
    # however.
    width, height = params.resolution
    client = WaylandClient()
    window = Rect.from_top_left(
        Point(0, 0),
        client.width_pixels,
        client.height_pixels
    )
    w = client.create_window(
        client.width_pixels,
        client.height_pixels,
        on_paint
    )
    reader.start()
    client.run()
