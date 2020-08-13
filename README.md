# Readme

*Cairo Sandbox* is an interactive sandbox for the cairo vector
graphics library.

Cairo is a wonderful library, but it can be hard to experiment with,
and it can be time-consuming to set up a context for
experimentation. It can also be hard to reason about transforms
without interactive feedback.

*Cairo Sandbox* Targeted at anyone who needs to do custom drawing
with cairo -- whether you're trying to develp a custom GTK Widget, or
visualizations for. The goal is to quickly get you up-and-runing with
a cairo context, then get out of your way while you hack.

It provides a number of useful features that an aid with developing
and debugging drawing.

- Instantly launch into a working cairo context ready for drawing.
- Automatic reload when your script changes.
- Debug feedback:
 - Current point and un-rasterized cairo path are shown
 - Exceptions and stack traces are displayed in real-time.
- Create live-editable parameters for easy tinkering.
- Automatically decodes JSON data from `stdin`, allowing you to
  experiment with values coming from arbitrary sources.

# Usage

Basic usage is as simple as: `./cairo_sandbox <file>`

If you have a data source which can output JSON to `stdout`, you can
pipe it into cairo sandbox, like so:

`my_json_source | ./cairo_sandbox <file>`

**TBD** Add a more compelling example and demo of this feature.

# API

See the `helpers` companion library, alongside this script.

- `pycairo`: https://pycairo.readthedocs.io/en/latest/getting_started.html

## Modes

You script runs in two modes, identifiable via the `__name__`
global. These modes are:

- `'init'`
- `'render'`

### Init Mode

Init mode is run whenver your script is reloaded. This is when your
script should define parameters. This mode can also be used for
one-time slow operations, such as pre-computing large arrays or
loading images off disk.

See `examples/parameters.py`.

Init Mode Globals:

- `params`, a `helpers.ParameterGroup` instance.

In addition, each of the `helpers.Parameter` classes is available
under a short ailias.

- `Numeric`
- `Color`
- `Text`
- `Font`
- `Table`
- `Point`
- `Angle`
- `Infinite`
- `Toggle`
- `Choice`
- `Image`
- `Script`
- `Custom`

### Render Mode

Render mode is run to draw each frame. The entire window is always
redrawn completely for each frame.

Render Mode Globals:

- `cr`: the cairo context object
- `cairo`: the pycairo library
- `helpers`: the companion helper object, which extends the cr object
- `math`: the math standard library, which includes useful items like `sin` and `pi`.
  with additional methods.
- `window`: a `helpers.Rect` object with the current window geometry
- `scale_mm`: a tuple of (x, y) indicating the scale for calculating physical distances
- `stdin`: A `dict` containing the most recent JSON object decoded from stdin.
- `mouse`: An object relfecting the current pointer state, TBD.

# Installation

Not necessary, not possible at the moment. Installation scripts are TBD.

## Dependencies

Requires gobject introspection libraries for `Gtk`, `pycairo`. Auto
reload `pyinotify`.

## Debian

TBD
