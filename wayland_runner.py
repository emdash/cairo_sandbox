#!/usr/bin/python3
#
# Copyright 2020 Brandon Lewis
#
# Heavily inspired by "surface.py" by Sean Vig, in the pywayland
# examples directory. Adapted and expanded for this use-case.

# TODOS:
# - allow for keyboard interrupt to work, plus some way for graceful exit.
# - allow for window to automatically match the output resolution
# - do we need explicit double buffering, or does wayland do this?
# - damage region optimizations.


import math
import mmap
import os
import time
import sys

import cairo


from pywayland.client import Display
from pywayland.protocol.wayland import WlCompositor, WlShell, WlShm
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

    def __init__(self, client):
        self.format = wayland_format_to_cairo_format(client.best_format())

        self.surface = client.compositor.create_surface()
        
        self.shell_surface = client.shell.get_shell_surface(self.surface)
        self.shell_surface.dispatcher["ping"] = self.ping_handler
        self.set_fullscreen()

        self.frame_callback = self.surface.frame()
        self.frame_callback.dispatcher["done"] = self.redraw

        self.shm_data, self.buffer = client.create_buffer()
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
            WIDTH,
            HEIGHT,
            stride_for_format(WIDTH, self.format))
    
    def redraw(self, callback, time, destroy_callback=True):
        if destroy_callback:
            callback._destroy()
    
        self.cr.save()
        self.paint(self.cr)
        self.cr.restore()
        self.surface.damage(0, 0, WIDTH, HEIGHT)
    
        callback = self.surface.frame()
        callback.dispatcher["done"] = self.redraw
    
        self.surface.attach(self.buffer, 0, 0)
        self.surface.commit()
    
    def paint(self, cr):
        # TODO: create script object.
        cr.set_source_rgb(0, 0, 0)
        cr.paint()
        cr.translate(WIDTH / 2, HEIGHT / 2)
        cr.rotate(time.time())
        cr.rectangle(-75, -75, 150, 150)
        cr.set_source_rgb(1, 1, 1)
        cr.set_line_width(15.0)
        cr.stroke()


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

        self.display.connect()
        print("connected to display")

        registry = self.display.get_registry()
        registry.dispatcher["global"] = self.handler
        # registry.dispatcher["global_remove"] = registry_global_remover

        self.display.dispatch(block=True)
        self.display.roundtrip()

        if self.compositor is None:
            raise RuntimeError("no compositor found")
        elif self.shell is None:
            raise RuntimeError("no shell found")
        elif self.shm is None:
            raise RuntimeError("no shm found")

        self.connected = True

    def create_window(self):
        self.ensure_connected()
        return Window(self)
        
    def handler(self, registry, id_, interface, version):
        if interface == "wl_compositor":
            self.compositor = registry.bind(id_, WlCompositor, version)
        elif interface == "wl_shell":
            self.shell = registry.bind(id_, WlShell, version)
        elif interface == "wl_shm":
            self.shm = registry.bind(id_, WlShm, version)
            self.shm.dispatcher["format"] = self.shm_format_handler

    def run(self):
        self.ensure_connected()
        while self.display.dispatch(block=True) != -1:
            pass
        time.sleep(1)
        display.disconnect()

    def shm_format_handler(self, unused, format_):
        self.formats.add(WlShm.format(format_))

    def create_buffer(self):
        stride = stride_for_format(WIDTH, client.best_format())
        size = stride * HEIGHT

        with AnonymousFile(size) as fd:
            shm_data = mmap.mmap(
                fd,
                size,
                prot=mmap.PROT_READ | mmap.PROT_WRITE,
                flags=mmap.MAP_SHARED)
            pool = client.shm.create_pool(fd, size)
            buff = pool.create_buffer(
                0,
                WIDTH,
                HEIGHT,
                stride,
                WlShm.format.argb8888.value)
            pool.destroy()
            return shm_data, buff

    def best_format(self):
        for f in self.preferred_formats:
            if f in self.formats:
                return f
        raise ValueError("No supported formats!")

if __name__ == "__main__":
    client = WaylandClient()
    w = client.create_window()
    client.run()
