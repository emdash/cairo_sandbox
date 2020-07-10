# Readme

*Cairo Explorer* is an interactive sandbox for the cairo vector
graphics library.

Cairo is a wonderful library, but it can be hard to experiment with it
in the context of a full application. This tool allows for interactive
coding with cairo, allowing for rapid prototyping.

It provides a number of useful features that an aid with developing
and debugging drawing.

- Automatic reload
- Debug facilities (tbd).
- Param interface for live editing of values (tbd).
- Fullscreen mode for presentation.

# Usage

`./cairo_explorer <file>`

# About

Cairo explorer provies a quick way to experiment with vector graphics.

Watches the given python script, automatically reloading as
necessary. It will execute the script in response to `paint` events on
the given window.

The file is a plain python script, you can do most things you'd normally
do in python. Do keep in mind that the 

# API

See the `helpers` companion library, alongside this script.

- `pycairo`: *TBD link to pycairo docs*

Provided Globals:

- `cr`: the cairo context object
- `cairo`: the pycairo library
- `helpers`: the companion helper library.
- `window`: a `helpers.Rect` object with the current window geometry
- `scale_mm`: a tuple of (x, y) indicating the scale for calculating physical distances

# Installation

Not necessary, TBD.

## Dependencies

Requires gobject introspection libraries for `Gtk`, `pycairo`, and
`pyinotify`.

## Debian

TBD
